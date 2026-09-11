require "sketchup.rb"
require "socket"
require "json"
require "base64"
require "tmpdir"

module TuSketchupAgent
  extend self

  HOST = "127.0.0.1" unless const_defined?(:HOST)
  PORT = 9876 unless const_defined?(:PORT)
  TOKEN = "tu-local-secret" unless const_defined?(:TOKEN)
  MAX_DIMENSION_MM = 1_000_000 unless const_defined?(:MAX_DIMENSION_MM)
  PROTOCOL_VERSION = "1.3"
  MIN_COMPATIBLE_PROTOCOL_VERSION = "1.0"

  @server ||= nil
  @timer_id ||= nil
  @started ||= false
  @managed_threads ||= []
  @dev_mode = false
  @model_revision ||= 0

  def running?
    @started && !@server.nil? && !@server.closed?
  end

  def dev_mode?
    ENV["TU_SKETCHUP_DEV_MODE"] == "1" || @dev_mode == true
  end

  def dev_mode=(val)
    @dev_mode = !!val
  end

  def model_revision
    @model_revision ||= 0
  end

  def bump_model_revision
    @model_revision = (@model_revision || 0) + 1
  end

  # ==========================================
  # Resource & Lifecycle Management
  # ==========================================

  def cleanup_resources
    @managed_threads.each do |thread|
      thread.kill if thread.alive? rescue nil
    end
    @managed_threads.clear

    if @server && !@server.closed?
      @server.close rescue nil
    end
  rescue StandardError => e
    puts "TuSketchupAgent cleanup error: #{e.message}"
  ensure
    @server = nil
    @started = false
  end

  def set_socket_timeout(socket, seconds = 5)
    if Gem.win_platform? || RUBY_PLATFORM =~ /mswin|mingw|cygwin/
      # Windows Winsock expects DWORD in milliseconds (4 bytes)
      timeout_ms = (seconds * 1000).to_i
      socket.setsockopt(Socket::SOL_SOCKET, Socket::SO_RCVTIMEO, [timeout_ms].pack("i"))
      socket.setsockopt(Socket::SOL_SOCKET, Socket::SO_SNDTIMEO, [timeout_ms].pack("i"))
    else
      # POSIX expects struct timeval (seconds, microseconds)
      timeval = [seconds.to_i, 0].pack("l_2")
      socket.setsockopt(Socket::SOL_SOCKET, Socket::SO_RCVTIMEO, timeval)
      socket.setsockopt(Socket::SOL_SOCKET, Socket::SO_SNDTIMEO, timeval)
    end
  rescue StandardError => e
    puts "TuSketchupAgent socket timeout warning: #{e.message}"
  end

  def with_operation(model, name, transparent = false)
    started = false
    model.start_operation(name, true, false, transparent)
    started = true
    result = yield
    started = false
    model.commit_operation
    result
  rescue StandardError
    model.abort_operation if started
    raise
  end

  def validate_dimension!(value, name)
    raise ArgumentError, "#{name} phải lớn hơn 0" unless value > 0
    raise ArgumentError, "#{name} (#{value} mm) vượt giới hạn tối đa #{MAX_DIMENSION_MM} mm" if value > MAX_DIMENSION_MM
  end

  def apply_material_to_group(group, model, material_name)
    return if material_name.to_s.empty?

    material = model.materials[material_name] || model.materials.add(material_name)
    group.material = material
    group.entities.grep(Sketchup::Face).each do |face|
      face.material = material
      face.back_material = material
    end
  end

  def validate_group_or_component!(entity)
    unless entity.is_a?(Sketchup::Group) || entity.is_a?(Sketchup::ComponentInstance)
      eid = entity.respond_to?(:persistent_id) ? entity.persistent_id : (entity.respond_to?(:entityID) ? entity.entityID : "unknown")
      raise ArgumentError, "Đối tượng ID #{eid} có kiểu #{entity.class.name} không được hỗ trợ. Chỉ hỗ trợ thao tác trên Sketchup::Group hoặc Sketchup::ComponentInstance."
    end
  end

  def build_transformation(args)
    # 1. Chế độ Raw Matrix 4x4 (16 số thực)
    if args["matrix"].is_a?(Array) && args["matrix"].length == 16
      raw_vals = args["matrix"].map { |v| Float(v) }
      return Geom::Transformation.new(raw_vals)
    end

    # 2. Chế độ tham số trực quan: Scale * Rotation * Translation
    # Scale
    t_scale = if args["scale"].is_a?(Array) && args["scale"].length == 3
      Geom::Transformation.scaling(Float(args["scale"][0]), Float(args["scale"][1]), Float(args["scale"][2]))
    elsif args["scale"] && Float(args["scale"]) != 1.0
      s = Float(args["scale"])
      Geom::Transformation.scaling(s, s, s)
    else
      Geom::Transformation.new
    end

    # Rotation
    t_rot = Geom::Transformation.new
    if args["rotation"].is_a?(Hash)
      axis_str = (args["rotation"]["axis"] || "z").to_s.downcase
      axis_vec = case axis_str
      when "x" then Geom::Vector3d.new(1, 0, 0)
      when "y" then Geom::Vector3d.new(0, 1, 0)
      else Geom::Vector3d.new(0, 0, 1)
      end
      angle_deg = Float(args["rotation"]["angle"] || 0.0)
      t_rot = Geom::Transformation.rotation(Geom::Point3d.new(0, 0, 0), axis_vec, angle_deg.degrees) if angle_deg != 0.0
    elsif args["rotation"].is_a?(Array) && args["rotation"].length == 3
      rx, ry, rz = args["rotation"].map { |v| Float(v) }
      tr_x = rx != 0 ? Geom::Transformation.rotation(Geom::Point3d.new(0, 0, 0), Geom::Vector3d.new(1, 0, 0), rx.degrees) : Geom::Transformation.new
      tr_y = ry != 0 ? Geom::Transformation.rotation(Geom::Point3d.new(0, 0, 0), Geom::Vector3d.new(0, 1, 0), ry.degrees) : Geom::Transformation.new
      tr_z = rz != 0 ? Geom::Transformation.rotation(Geom::Point3d.new(0, 0, 0), Geom::Vector3d.new(0, 0, 1), rz.degrees) : Geom::Transformation.new
      t_rot = tr_z * tr_y * tr_x
    end

    # Translation (Position in mm)
    t_pos = Geom::Transformation.new
    if args["position"].is_a?(Array) && args["position"].length >= 3
      px = Float(args["position"][0]).mm
      py = Float(args["position"][1]).mm
      pz = Float(args["position"][2]).mm
      t_pos = Geom::Transformation.translation(Geom::Point3d.new(px, py, pz))
    end

    t_pos * t_rot * t_scale
  end

  def material_metadata(mat)
    return nil unless mat && mat.valid?
    c = mat.color
    tex = mat.texture
    {
      name: mat.name,
      display_name: mat.display_name,
      color_rgb: [c.red, c.green, c.blue, c.alpha],
      color_hex: sprintf("#%02X%02X%02X", c.red, c.green, c.blue),
      alpha: mat.alpha.round(3),
      has_texture: !tex.nil?,
      texture: tex ? {
        filename: tex.filename,
        width_mm: tex.width.to_mm.round(1),
        height_mm: tex.height.to_mm.round(1)
      } : nil
    }
  end

  def entity_metadata(entity)
    return nil unless entity
    pid = entity.respond_to?(:persistent_id) ? entity.persistent_id : nil
    eid = entity.entityID
    {
      entity_id: eid,
      persistent_id: pid,
      type: entity.class.name.sub("Sketchup::", ""),
      name: entity.respond_to?(:name) ? entity.name : nil,
      layer: entity.respond_to?(:layer) && entity.layer ? entity.layer.name : "Layer0"
    }
  end

  def find_entity_by_persistent_id(model, id)
    return nil unless model && id
    return nil if id.to_s.strip.empty?
    int_id = Integer(id)
    return nil if int_id <= 0

    entity = model.find_entity_by_persistent_id(int_id) if model.respond_to?(:find_entity_by_persistent_id)
    return nil unless entity
    return nil if entity.respond_to?(:valid?) && !entity.valid?

    entity
  rescue ArgumentError, TypeError
    nil
  end

  def find_entity_recursive(entities, entity_id)
    return nil unless entities
    entities.each do |entity|
      return entity if entity.respond_to?(:entityID) && entity.entityID == entity_id
      if entity.is_a?(Sketchup::Group)
        found = find_entity_recursive(entity.entities, entity_id)
        return found if found
      elsif entity.is_a?(Sketchup::ComponentInstance)
        found = find_entity_recursive(entity.definition.entities, entity_id)
        return found if found
      end
    end
    nil
  end

  def find_entity_by_id(model, id)
    return nil unless model && id
    return nil if id.to_s.strip.empty?
    int_id = Integer(id)
    return nil if int_id <= 0

    entity = model.find_entity_by_id(int_id) if model.respond_to?(:find_entity_by_id)
    entity = find_entity_recursive(model.entities, int_id) if entity.nil?
    entity = find_entity_recursive(model.active_entities, int_id) if entity.nil? && model.respond_to?(:active_entities) && model.active_entities != model.entities
    return nil unless entity
    return nil if entity.respond_to?(:valid?) && !entity.valid?

    entity
  rescue ArgumentError, TypeError
    nil
  end

  def find_entity(model, target)
    return nil unless model && target

    if target.is_a?(Hash)
      if target["persistent_id"]
        find_entity_by_persistent_id(model, target["persistent_id"])
      elsif target["entity_id"]
        find_entity_by_id(model, target["entity_id"])
      elsif target["reference_id"]
        find_entity_by_persistent_id(model, target["reference_id"])
      elsif target["parent_id"]
        find_entity_by_persistent_id(model, target["parent_id"]) || find_entity_by_id(model, target["parent_id"])
      elsif target["id"]
        find_entity_by_persistent_id(model, target["id"]) || find_entity_by_id(model, target["id"])
      end
    else
      find_entity_by_persistent_id(model, target) || find_entity_by_id(model, target)
    end
  end

  def ping_response
    {
      ok: true,
      service: "tu-sketchup-agent",
      protocol_version: PROTOCOL_VERSION,
      min_compatible_protocol_version: MIN_COMPATIBLE_PROTOCOL_VERSION,
      sketchup_version: Sketchup.version,
      server: "#{HOST}:#{PORT}",
      dev_mode: dev_mode?
    }
  end

  def ping
    UI.messagebox("Tu SketchUp Agent đang hoạt động.\nServer port #{PORT}: #{running? ? 'RUNNING (Main Thread)' : 'STOPPED'}\nDev Mode: #{dev_mode? ? 'BẬT' : 'TẮT'}")
  end

  # ==========================================
  # Dispatch API Handlers - State Inspection
  # ==========================================

  def model_summary
    model = Sketchup.active_model
    raise "Không có model nào đang mở" unless model

    bbox = model.bounds
    {
      ok: true,
      service: "tu-sketchup-agent",
      protocol_version: PROTOCOL_VERSION,
      min_compatible_protocol_version: MIN_COMPATIBLE_PROTOCOL_VERSION,
      sketchup_version: Sketchup.version,
      model_revision: model_revision,
      mcp_revision: model_revision,
      model_revision_source: "tu-sketchup-agent",
      capabilities: {
        find_entity_by_persistent_id: model.respond_to?(:find_entity_by_persistent_id),
        find_entity_by_id: model.respond_to?(:find_entity_by_id)
      },
      title: model.title.empty? ? "Untitled" : model.title,
      path: model.path,
      entity_count: model.active_entities.length,
      selection_count: model.selection.length,
      layers: model.layers.map(&:name),
      materials: model.materials.map(&:name),
      scenes: model.pages.map(&:name),
      bounds_mm: {
        width: bbox.width.to_mm.round(1),
        depth: bbox.height.to_mm.round(1),
        height: bbox.depth.to_mm.round(1)
      }
    }
  end

  def get_selection
    model = Sketchup.active_model
    raise "Không có model nào đang mở" unless model

    items = model.selection.map do |entity|
      bbox = entity.respond_to?(:bounds) ? entity.bounds : nil
      meta = entity_metadata(entity)
      meta.merge(
        material: entity.respond_to?(:material) && entity.material ? entity.material.name : nil,
        bounds_mm: bbox ? {
          width: bbox.width.to_mm.round(1),
          depth: bbox.height.to_mm.round(1),
          height: bbox.depth.to_mm.round(1),
          center: [bbox.center.x.to_mm.round(1), bbox.center.y.to_mm.round(1), bbox.center.z.to_mm.round(1)]
        } : nil
      )
    end

    { ok: true, count: items.length, items: items }
  end

  def get_entities(args)
    model = Sketchup.active_model
    raise "Không có model nào đang mở" unless model

    requested_id = args["parent_id"] || args["persistent_id"] || args["entity_id"] || args["reference_id"]
    parent = nil
    parent_context = nil
    target_entities = model.active_entities

    if requested_id
      parent = if args["persistent_id"]
        find_entity_by_persistent_id(model, args["persistent_id"])
      elsif args["entity_id"]
        find_entity_by_id(model, args["entity_id"])
      elsif args["reference_id"]
        find_entity_by_persistent_id(model, args["reference_id"])
      elsif args["parent_id"]
        find_entity_by_persistent_id(model, args["parent_id"]) || find_entity_by_id(model, args["parent_id"])
      end

      raise ArgumentError, "Không tìm thấy parent entity với ID #{requested_id}" unless parent

      if parent.is_a?(Sketchup::ComponentInstance)
        target_entities = parent.definition.entities
        t = parent.transformation
        parent_context = {
          type: "component_definition",
          coordinate_space: "component_definition_local",
          definition_name: parent.definition.name,
          instance: entity_metadata(parent),
          transformation: {
            origin_mm: [t.origin.x.to_mm.round(1), t.origin.y.to_mm.round(1), t.origin.z.to_mm.round(1)],
            xscale: t.xscale.round(4),
            yscale: t.yscale.round(4),
            zscale: t.zscale.round(4)
          }
        }
      elsif parent.respond_to?(:entities)
        target_entities = parent.entities
        t = parent.respond_to?(:transformation) ? parent.transformation : nil
        parent_context = {
          type: "group_container",
          coordinate_space: "group_container_local",
          parent: entity_metadata(parent),
          transformation: t ? {
            origin_mm: [t.origin.x.to_mm.round(1), t.origin.y.to_mm.round(1), t.origin.z.to_mm.round(1)],
            xscale: t.xscale.round(4),
            yscale: t.yscale.round(4),
            zscale: t.zscale.round(4)
          } : nil
        }
      else
        raise ArgumentError, "Entity ID #{requested_id} không chứa danh sách entities con"
      end
    end

    type_filter = args["type_filter"].to_s.strip
    layer_filter = args["layer_filter"].to_s.strip
    name_filter = args["name_filter"].to_s.strip
    limit = (args["limit"] || 100).to_i.clamp(1, 1000)
    offset = (args["offset"] || 0).to_i
    offset = 0 if offset < 0

    all_list = target_entities.to_a

    filtered = all_list.select do |e|
      match = true

      if !type_filter.empty?
        class_name = e.class.name.sub("Sketchup::", "")
        match = false unless class_name.casecmp?(type_filter)
      end

      if match && !layer_filter.empty?
        layer_name = e.respond_to?(:layer) && e.layer ? e.layer.name : "Layer0"
        match = false unless layer_name.casecmp?(layer_filter)
      end

      if match && !name_filter.empty?
        name_str = e.respond_to?(:name) ? e.name.to_s : ""
        match = false unless name_str.downcase.include?(name_filter.downcase)
      end

      match
    end

    sliced = filtered.slice(offset, limit) || []

    items = sliced.map do |e|
      meta = entity_metadata(e)
      bbox = e.respond_to?(:bounds) ? e.bounds : nil
      meta.merge(
        visible: e.respond_to?(:visible?) ? e.visible? : true,
        material: e.respond_to?(:material) && e.material ? e.material.name : nil,
        bounds_mm: bbox ? {
          width: bbox.width.to_mm.round(1),
          depth: bbox.height.to_mm.round(1),
          height: bbox.depth.to_mm.round(1),
          center: [bbox.center.x.to_mm.round(1), bbox.center.y.to_mm.round(1), bbox.center.z.to_mm.round(1)]
        } : nil
      )
    end

    is_root = model.active_path.nil? || model.active_path.empty?
    active_context = if is_root
      { type: "root", name: "Model Root" }
    else
      curr = model.active_path.last
      {
        type: curr.class.name.sub("Sketchup::", ""),
        name: curr.respond_to?(:name) ? curr.name : nil,
        persistent_id: curr.respond_to?(:persistent_id) ? curr.persistent_id : nil,
        depth: model.active_path.length
      }
    end

    {
      ok: true,
      total_count: filtered.length,
      returned_count: items.length,
      offset: offset,
      limit: limit,
      active_context: active_context,
      parent_context: parent_context,
      items: items
    }
  end

  def get_entity_info(args)
    model = Sketchup.active_model
    raise "Không có model nào đang mở" unless model

    entity = if args["persistent_id"]
      find_entity_by_persistent_id(model, args["persistent_id"])
    elsif args["entity_id"]
      find_entity_by_id(model, args["entity_id"])
    elsif args["reference_id"]
      find_entity_by_persistent_id(model, args["reference_id"])
    else
      raise ArgumentError, "Thiếu tham số persistent_id hoặc entity_id"
    end

    raise ArgumentError, "Không tìm thấy đối tượng hợp lệ với ID cung cấp" unless entity && entity.valid?

    meta = entity_metadata(entity)
    bbox = entity.respond_to?(:bounds) ? entity.bounds : nil

    info = {
      ok: true,
      entity: meta,
      valid: entity.valid?,
      hidden: entity.respond_to?(:hidden?) ? entity.hidden? : false,
      locked: entity.respond_to?(:locked?) ? entity.locked? : false,
      material: entity.respond_to?(:material) && entity.material ? entity.material.name : nil
    }

    if bbox
      info[:bounds_mm] = {
        width: bbox.width.to_mm.round(1),
        depth: bbox.height.to_mm.round(1),
        height: bbox.depth.to_mm.round(1),
        center: [bbox.center.x.to_mm.round(1), bbox.center.y.to_mm.round(1), bbox.center.z.to_mm.round(1)],
        min: [bbox.min.x.to_mm.round(1), bbox.min.y.to_mm.round(1), bbox.min.z.to_mm.round(1)],
        max: [bbox.max.x.to_mm.round(1), bbox.max.y.to_mm.round(1), bbox.max.z.to_mm.round(1)]
      }
    end

    if entity.is_a?(Sketchup::Group)
      info[:children_count] = entity.entities.length
      t = entity.transformation
      info[:transformation] = {
        position_mm: [t.origin.x.to_mm.round(1), t.origin.y.to_mm.round(1), t.origin.z.to_mm.round(1)],
        xscale: t.xscale.round(4),
        yscale: t.yscale.round(4),
        zscale: t.zscale.round(4)
      }
    elsif entity.is_a?(Sketchup::ComponentInstance)
      info[:definition_name] = entity.definition.name
      info[:children_count] = entity.definition.entities.length
      t = entity.transformation
      info[:transformation] = {
        position_mm: [t.origin.x.to_mm.round(1), t.origin.y.to_mm.round(1), t.origin.z.to_mm.round(1)],
        xscale: t.xscale.round(4),
        yscale: t.yscale.round(4),
        zscale: t.zscale.round(4)
      }
    elsif entity.is_a?(Sketchup::Face)
      info[:area_mm2] = (entity.area * 25.4 * 25.4).round(1)
      info[:back_material] = entity.back_material ? entity.back_material.name : nil
      info[:normal] = [entity.normal.x.round(4), entity.normal.y.round(4), entity.normal.z.round(4)]
      info[:vertices_count] = entity.vertices.length
    elsif entity.is_a?(Sketchup::Edge)
      info[:length_mm] = entity.length.to_mm.round(1)
      info[:start_point_mm] = [entity.start.position.x.to_mm.round(1), entity.start.position.y.to_mm.round(1), entity.start.position.z.to_mm.round(1)]
      info[:end_point_mm] = [entity.end.position.x.to_mm.round(1), entity.end.position.y.to_mm.round(1), entity.end.position.z.to_mm.round(1)]
    end

    info
  end

  def get_bounding_box(args)
    model = Sketchup.active_model
    raise "Không có model nào đang mở" unless model

    items = []
    if args["persistent_ids"]
      Array(args["persistent_ids"]).each { |id| items << [:pid, id] }
    elsif args["entity_ids"]
      Array(args["entity_ids"]).each { |id| items << [:eid, id] }
    elsif args["persistent_id"]
      items << [:pid, args["persistent_id"]]
    elsif args["entity_id"]
      items << [:eid, args["entity_id"]]
    elsif args["reference_ids"]
      Array(args["reference_ids"]).each { |id| items << [:ref, id] }
    elsif args["reference_id"]
      items << [:ref, args["reference_id"]]
    end

    raise ArgumentError, "Cần danh sách ID đối tượng không rỗng" if items.empty?
    raise ArgumentError, "Tối đa 1000 đối tượng mỗi request (nhận #{items.length})" if items.length > 1000

    combined_bb = Geom::BoundingBox.new
    found_count = 0
    missing_ids = []

    items.each do |type, id|
      e = case type
      when :pid then find_entity_by_persistent_id(model, id)
      when :eid then find_entity_by_id(model, id)
      when :ref then find_entity_by_persistent_id(model, id)
      end

      if e && e.valid? && e.respond_to?(:bounds)
        combined_bb.add(e.bounds)
        found_count += 1
      else
        missing_ids << id
      end
    end

    raise ArgumentError, "Không tìm thấy đối tượng nào hợp lệ trong danh sách ID cung cấp" if found_count == 0

    {
      ok: true,
      found_count: found_count,
      missing_ids: missing_ids,
      bounds_mm: {
        width: combined_bb.width.to_mm.round(1),
        depth: combined_bb.height.to_mm.round(1),
        height: combined_bb.depth.to_mm.round(1),
        center: [combined_bb.center.x.to_mm.round(1), combined_bb.center.y.to_mm.round(1), combined_bb.center.z.to_mm.round(1)],
        min: [combined_bb.min.x.to_mm.round(1), combined_bb.min.y.to_mm.round(1), combined_bb.min.z.to_mm.round(1)],
        max: [combined_bb.max.x.to_mm.round(1), combined_bb.max.y.to_mm.round(1), combined_bb.max.z.to_mm.round(1)]
      }
    }
  end

  def get_materials(args)
    model = Sketchup.active_model
    raise "Không có model nào đang mở" unless model

    limit = (args["limit"] || 100).to_i.clamp(1, 1000)
    offset = (args["offset"] || 0).to_i
    offset = 0 if offset < 0
    name_filter = args["name_filter"].to_s.strip.downcase

    all_mats = model.materials.to_a
    if !name_filter.empty?
      all_mats.select! { |m| m.name.downcase.include?(name_filter) }
    end

    total_count = all_mats.length
    sliced = all_mats.slice(offset, limit) || []
    items = sliced.map { |m| material_metadata(m) }

    {
      ok: true,
      total_count: total_count,
      returned_count: items.length,
      offset: offset,
      limit: limit,
      materials: items,
      protocol_version: PROTOCOL_VERSION,
      min_compatible_protocol_version: MIN_COMPATIBLE_PROTOCOL_VERSION
    }
  end

  def get_material_info(args)
    model = Sketchup.active_model
    raise "Không có model nào đang mở" unless model

    name = (args["name"] || args["material_name"]).to_s.strip
    raise ArgumentError, "Thiếu tham số tên vật liệu (name hoặc material_name)" if name.empty?

    mat = model.materials[name]
    raise ArgumentError, "Không tìm thấy vật liệu có tên '#{name}' trong model" unless mat

    {
      ok: true,
      material: material_metadata(mat),
      protocol_version: PROTOCOL_VERSION,
      min_compatible_protocol_version: MIN_COMPATIBLE_PROTOCOL_VERSION
    }
  end

  def get_entity_attributes(args)
    model = Sketchup.active_model
    raise "Không có model nào đang mở" unless model

    target = args["persistent_id"] || args["entity_id"] || args["id"]
    raise ArgumentError, "Cần cung cấp ID đối tượng (persistent_id hoặc entity_id)" unless target

    entity = if args["persistent_id"]
      find_entity_by_persistent_id(model, args["persistent_id"])
    elsif args["entity_id"]
      find_entity_by_id(model, args["entity_id"])
    else
      find_entity(model, target)
    end
    raise ArgumentError, "Không tìm thấy đối tượng với ID #{target}" unless entity

    dict_filter = args["dictionary_name"].to_s.strip
    dictionaries = {}

    if !dict_filter.empty?
      dict = entity.attribute_dictionary(dict_filter, false)
      if dict
        d_hash = {}
        dict.each { |k, v| d_hash[k] = v }
        dictionaries[dict_filter] = d_hash
      end
    elsif entity.attribute_dictionaries
      entity.attribute_dictionaries.each do |d|
        d_hash = {}
        d.each { |k, v| d_hash[k] = v }
        dictionaries[d.name] = d_hash
      end
    end

    {
      ok: true,
      entity: entity_metadata(entity),
      dictionary_count: dictionaries.keys.length,
      dictionaries: dictionaries,
      protocol_version: PROTOCOL_VERSION,
      min_compatible_protocol_version: MIN_COMPATIBLE_PROTOCOL_VERSION
    }
  end

  # ==========================================
  # Dispatch API Handlers - Geometry Creation
  # ==========================================

  def execute_ruby(args)
    unless dev_mode?
      return {
        ok: false,
        error: {
          code: "DEV_MODE_REQUIRED",
          message: "execute_ruby bị vô hiệu hóa ngoài dev mode (bật TU_SKETCHUP_DEV_MODE=1 hoặc qua menu Extension)",
          class: "SecurityError"
        }
      }
    end

    code = args["code"].to_s
    if code.strip.empty?
      return {
        ok: false,
        error: {
          code: "INVALID_ARGUMENT",
          message: "Thiếu code ruby"
        }
      }
    end

    if code.bytesize > 100_000
      return {
        ok: false,
        error: {
          code: "PAYLOAD_TOO_LARGE",
          message: "Code vượt quá giới hạn 100 KB"
        }
      }
    end

    auto_op = args.fetch("auto_operation", false)
    model = Sketchup.active_model

    puts "TuSketchupAgent: [execute_ruby] #{code.slice(0, 80).strip}..."

    result = nil
    if auto_op && model
      with_operation(model, "AI Ruby Execution") do
        result = eval(code, TOPLEVEL_BINDING)
        bump_model_revision
      end
    else
      # Read-only path: eval without wrapping operation or bumping revision
      result = eval(code, TOPLEVEL_BINDING)
    end

    {
      ok: true,
      result: result.inspect,
      class: result.class.name,
      model_revision: model_revision,
      mcp_revision: model_revision
    }
  rescue StandardError => error
    err = {
      code: "RUBY_EXECUTION_ERROR",
      message: error.message,
      class: error.class.name
    }
    err[:backtrace] = error.backtrace.first(5) if dev_mode? && error.backtrace
    {
      ok: false,
      error: err
    }
  end

  def create_box(args)
    width = Float(args.fetch("width"))
    depth = Float(args.fetch("depth"))
    height = Float(args.fetch("height"))

    validate_dimension!(width, "width")
    validate_dimension!(depth, "depth")
    validate_dimension!(height, "height")

    x = Float(args["x"] || 0.0)
    y = Float(args["y"] || 0.0)
    z = Float(args["z"] || 0.0)
    name = args["name"].to_s
    material_name = args["material"].to_s

    model = Sketchup.active_model
    raise "Không có model nào đang mở" unless model

    group = nil
    with_operation(model, "AI - Create Box") do
      group = model.active_entities.add_group
      group.name = name unless name.empty?
      entities = group.entities

      p1 = [x.mm, y.mm, z.mm]
      p2 = [(x + width).mm, y.mm, z.mm]
      p3 = [(x + width).mm, (y + depth).mm, z.mm]
      p4 = [x.mm, (y + depth).mm, z.mm]

      face = entities.add_face(p1, p2, p3, p4)
      raise "Không thể tạo mặt đáy" unless face
      face.reverse! if face.normal.z < 0
      face.pushpull(height.mm)

      apply_material_to_group(group, model, material_name)
      bump_model_revision
    end

    {
      ok: true,
      operation: "create_box",
      entity: entity_metadata(group),
      dimensions_mm: { width: width, depth: depth, height: height },
      position_mm: [x, y, z],
      material: material_name.empty? ? nil : material_name,
      model_revision: model_revision
    }
  end

  def create_cylinder(args)
    radius = Float(args.fetch("radius"))
    height = Float(args.fetch("height"))

    validate_dimension!(radius, "radius")
    validate_dimension!(height, "height")

    segments = Integer(args["segments"] || 24)
    raise ArgumentError, "segments phải trong khoảng 3..256" unless segments.between?(3, 256)

    x = Float(args["x"] || 0.0)
    y = Float(args["y"] || 0.0)
    z = Float(args["z"] || 0.0)
    name = args["name"].to_s
    material_name = args["material"].to_s

    model = Sketchup.active_model
    raise "Không có model nào đang mở" unless model

    group = nil
    with_operation(model, "AI - Create Cylinder") do
      group = model.active_entities.add_group
      group.name = name unless name.empty?
      entities = group.entities

      circle = entities.add_circle([x.mm, y.mm, z.mm], [0, 0, 1], radius.mm, segments)
      face = entities.add_face(circle)
      raise "Không thể tạo mặt đáy hình trụ" unless face
      face.reverse! if face.normal.z < 0
      face.pushpull(height.mm)

      apply_material_to_group(group, model, material_name)
      bump_model_revision
    end

    {
      ok: true,
      operation: "create_cylinder",
      entity: entity_metadata(group),
      radius_mm: radius,
      height_mm: height,
      segments: segments,
      position_mm: [x, y, z],
      material: material_name.empty? ? nil : material_name,
      model_revision: model_revision
    }
  end

  def create_wall(args)
    start_x = Float(args.fetch("start_x"))
    start_y = Float(args.fetch("start_y"))
    end_x = Float(args.fetch("end_x"))
    end_y = Float(args.fetch("end_y"))
    thickness = Float(args["thickness"] || 100.0)
    height = Float(args["height"] || 2800.0)
    z = Float(args["z"] || 0.0)
    name = args["name"].to_s.empty? ? "Wall" : args["name"].to_s
    material_name = args["material"].to_s

    validate_dimension!(thickness, "thickness")
    validate_dimension!(height, "height")

    dx = end_x - start_x
    dy = end_y - start_y
    length = Math.hypot(dx, dy)
    raise ArgumentError, "Chiều dài tường phải lớn hơn 0" if length <= 0
    validate_dimension!(length, "length")

    model = Sketchup.active_model
    raise "Không có model nào đang mở" unless model

    group = nil
    with_operation(model, "AI - Create Wall") do
      group = model.active_entities.add_group
      group.name = name
      entities = group.entities

      nx = (-dy / length) * (thickness / 2.0)
      ny = (dx / length) * (thickness / 2.0)

      p1 = [(start_x - nx).mm, (start_y - ny).mm, z.mm]
      p2 = [(end_x - nx).mm, (end_y - ny).mm, z.mm]
      p3 = [(end_x + nx).mm, (end_y + ny).mm, z.mm]
      p4 = [(start_x + nx).mm, (start_y + ny).mm, z.mm]

      face = entities.add_face(p1, p2, p3, p4)
      raise "Không thể tạo mặt tường" unless face
      face.reverse! if face.normal.z < 0
      face.pushpull(height.mm)

      apply_material_to_group(group, model, material_name)
      bump_model_revision
    end

    {
      ok: true,
      operation: "create_wall",
      entity: entity_metadata(group),
      length_mm: length.round(1),
      thickness_mm: thickness,
      height_mm: height,
      material: material_name.empty? ? nil : material_name,
      model_revision: model_revision
    }
  end

  def capture_viewport(args)
    width = (args["width"] || 1280).to_i
    height = (args["height"] || 720).to_i
    raise ArgumentError, "width phải trong khoảng 64..4096" unless width.between?(64, 4096)
    raise ArgumentError, "height phải trong khoảng 64..4096" unless height.between?(64, 4096)

    output_path = args["output_path"].to_s.strip
    is_temp = output_path.empty?
    target_file = is_temp ? File.join(Dir.tmpdir, "sketchup_vp_#{Time.now.to_i}_#{rand(1000)}.png") : output_path

    include_base64 = args.fetch("include_base64", false)

    model = Sketchup.active_model
    raise "Không có model nào đang mở" unless model

    view = model.active_view

    view.write_image({
      filename: target_file,
      width: width,
      height: height,
      antialias: true,
      compression: 0.9
    })

    image_written = File.exist?(target_file)
    b64_data = (include_base64 && image_written) ? Base64.strict_encode64(File.binread(target_file)) : nil

    {
      ok: true,
      width: width,
      height: height,
      image_path: is_temp ? nil : target_file,
      image_available: image_written,
      image_base64: b64_data
    }
  ensure
    File.delete(target_file) if is_temp && target_file && File.exist?(target_file)
  end

  def zoom_extents
    model = Sketchup.active_model
    raise "Không có model nào đang mở" unless model

    model.active_view.zoom_extents
    { ok: true, operation: "zoom_extents" }
  end

  # ==========================================
  # Dispatch API Handlers - Geometry Transformations
  # ==========================================

  def resolve_entities_from_args(model, args)
    raw_ids = []
    if args["ids"].is_a?(Array)
      raw_ids = args["ids"]
    elsif args["persistent_ids"].is_a?(Array)
      raw_ids = args["persistent_ids"].map { |id| { "persistent_id" => id } }
    elsif args["entity_ids"].is_a?(Array)
      raw_ids = args["entity_ids"].map { |id| { "entity_id" => id } }
    elsif args["id"]
      raw_ids = [args["id"]]
    elsif args["persistent_id"]
      raw_ids = [{ "persistent_id" => args["persistent_id"] }]
    elsif args["entity_id"]
      raw_ids = [{ "entity_id" => args["entity_id"] }]
    end

    raise ArgumentError, "Cần cung cấp ít nhất một ID đối tượng (ids, persistent_ids, entity_ids hoặc id)" if raw_ids.empty?

    entities = []
    missing_ids = []

    raw_ids.each do |item|
      entity = find_entity(model, item)
      if entity && entity.respond_to?(:valid?) && entity.valid?
        entities << entity
      else
        missing_ids << (item.is_a?(Hash) ? (item["persistent_id"] || item["entity_id"] || item["id"]) : item)
      end
    end

    [entities, missing_ids]
  end

  def calculate_bounds_mm(entities)
    bb = Geom::BoundingBox.new
    entities.each do |e|
      bb.add(e.bounds) if e && e.respond_to?(:bounds) && e.valid?
    end
    return nil if bb.empty?
    {
      width: bb.width.to_mm.round(1),
      depth: bb.height.to_mm.round(1),
      height: bb.depth.to_mm.round(1),
      center: [bb.center.x.to_mm.round(1), bb.center.y.to_mm.round(1), bb.center.z.to_mm.round(1)],
      min: [bb.min.x.to_mm.round(1), bb.min.y.to_mm.round(1), bb.min.z.to_mm.round(1)],
      max: [bb.max.x.to_mm.round(1), bb.max.y.to_mm.round(1), bb.max.z.to_mm.round(1)]
    }
  end

  def move_entities(args)
    model = Sketchup.active_model
    raise "Không có model nào đang mở" unless model

    dx = Float(args["dx"] || 0.0)
    dy = Float(args["dy"] || 0.0)
    dz = Float(args["dz"] || 0.0)

    vec = Geom::Vector3d.new(dx.mm, dy.mm, dz.mm)
    raise ArgumentError, "Vector dịch chuyển (dx, dy, dz) phải khác 0" if vec.length < 0.0001

    entities, missing_ids = resolve_entities_from_args(model, args)
    raise ArgumentError, "Không tìm thấy đối tượng nào hợp lệ để di chuyển" if entities.empty?

    t = Geom::Transformation.translation(vec)

    with_operation(model, "AI - Move Entities") do
      entities.each do |entity|
        if entity.respond_to?(:transform!)
          entity.transform!(t)
        elsif entity.parent && entity.parent.respond_to?(:entities)
          entity.parent.entities.transform_entities(t, [entity])
        else
          model.active_entities.transform_entities(t, [entity])
        end
      end
      bump_model_revision
    end

    {
      ok: true,
      operation: "move",
      moved_count: entities.length,
      missing_ids: missing_ids,
      vector_mm: [dx, dy, dz],
      entities: entities.map { |e| entity_metadata(e) },
      bounds_mm: calculate_bounds_mm(entities),
      model_revision: model_revision,
      mcp_revision: model_revision
    }
  end

  def copy_entities(args)
    model = Sketchup.active_model
    raise "Không có model nào đang mở" unless model

    dx = Float(args["dx"] || 0.0)
    dy = Float(args["dy"] || 0.0)
    dz = Float(args["dz"] || 0.0)

    vec = Geom::Vector3d.new(dx.mm, dy.mm, dz.mm)
    t = Geom::Transformation.translation(vec)

    entities, missing_ids = resolve_entities_from_args(model, args)
    raise ArgumentError, "Không tìm thấy đối tượng nào hợp lệ để sao chép" if entities.empty?

    new_entities = []

    with_operation(model, "AI - Copy Entities") do
      entities.each do |entity|
        if entity.is_a?(Sketchup::Group)
          copy_grp = entity.copy
          copy_grp.transform!(t) unless vec.length < 0.0001
          new_entities << copy_grp
        elsif entity.is_a?(Sketchup::ComponentInstance)
          container = entity.parent.is_a?(Sketchup::ComponentDefinition) ? entity.parent.entities : model.active_entities
          copy_inst = container.add_instance(entity.definition, entity.transformation * t)
          new_entities << copy_inst
        elsif entity.parent && entity.parent.respond_to?(:entities)
          copy_grp = model.active_entities.add_group([entity])
          dupe = copy_grp.copy
          dupe.transform!(t) unless vec.length < 0.0001
          new_entities.concat(dupe.explode.grep(Sketchup::Drawingelement))
          copy_grp.explode
        end
      end
      bump_model_revision
    end

    {
      ok: true,
      operation: "copy",
      copied_count: new_entities.length,
      missing_ids: missing_ids,
      vector_mm: [dx, dy, dz],
      entities: new_entities.map { |e| entity_metadata(e) },
      bounds_mm: calculate_bounds_mm(new_entities),
      model_revision: model_revision,
      mcp_revision: model_revision
    }
  end

  def rotate_entities(args)
    model = Sketchup.active_model
    raise "Không có model nào đang mở" unless model

    angle_deg = Float(args.fetch("angle_degrees"))
    raise ArgumentError, "Góc quay (angle_degrees) phải khác 0" if angle_deg.abs < 0.001

    axis_arg = args["axis"] || "z"
    axis_vec = case axis_arg.to_s.downcase
    when "x" then Geom::Vector3d.new(1, 0, 0)
    when "y" then Geom::Vector3d.new(0, 1, 0)
    when "z" then Geom::Vector3d.new(0, 0, 1)
    else
      if axis_arg.is_a?(Array) && axis_arg.length == 3
        Geom::Vector3d.new(Float(axis_arg[0]), Float(axis_arg[1]), Float(axis_arg[2]))
      else
        raise ArgumentError, "axis phải là 'x', 'y', 'z' hoặc mảng 3 phần tử [ax, ay, az]"
      end
    end
    raise ArgumentError, "Vector trục quay không hợp lệ (độ dài bằng 0)" if axis_vec.length < 0.0001
    axis_vec.normalize!

    entities, missing_ids = resolve_entities_from_args(model, args)
    raise ArgumentError, "Không tìm thấy đối tượng nào hợp lệ để xoay" if entities.empty?

    combined_bb = Geom::BoundingBox.new
    entities.each { |e| combined_bb.add(e.bounds) if e.respond_to?(:bounds) }

    origin_pt = if args["origin"].is_a?(Array) && args["origin"].length == 3
      Geom::Point3d.new(Float(args["origin"][0]).mm, Float(args["origin"][1]).mm, Float(args["origin"][2]).mm)
    else
      combined_bb.center
    end

    t = Geom::Transformation.rotation(origin_pt, axis_vec, angle_deg.degrees)

    with_operation(model, "AI - Rotate Entities") do
      entities.each do |entity|
        if entity.respond_to?(:transform!)
          entity.transform!(t)
        elsif entity.parent && entity.parent.respond_to?(:entities)
          entity.parent.entities.transform_entities(t, [entity])
        else
          model.active_entities.transform_entities(t, [entity])
        end
      end
      bump_model_revision
    end

    {
      ok: true,
      operation: "rotate",
      rotated_count: entities.length,
      missing_ids: missing_ids,
      axis: axis_arg,
      angle_degrees: angle_deg,
      origin_mm: [origin_pt.x.to_mm.round(1), origin_pt.y.to_mm.round(1), origin_pt.z.to_mm.round(1)],
      entities: entities.map { |e| entity_metadata(e) },
      bounds_mm: calculate_bounds_mm(entities),
      model_revision: model_revision,
      mcp_revision: model_revision
    }
  end

  def scale_entities(args)
    model = Sketchup.active_model
    raise "Không có model nào đang mở" unless model

    x_scale = Float(args["x_scale"] || args["scale"] || 1.0)
    y_scale = Float(args["y_scale"] || args["scale"] || 1.0)
    z_scale = Float(args["z_scale"] || args["scale"] || 1.0)

    raise ArgumentError, "Tỷ lệ scale x_scale, y_scale, z_scale phải khác 0" if x_scale == 0 || y_scale == 0 || z_scale == 0

    entities, missing_ids = resolve_entities_from_args(model, args)
    raise ArgumentError, "Không tìm thấy đối tượng nào hợp lệ để scale" if entities.empty?

    combined_bb = Geom::BoundingBox.new
    entities.each { |e| combined_bb.add(e.bounds) if e.respond_to?(:bounds) }

    origin_pt = if args["origin"].is_a?(Array) && args["origin"].length == 3
      Geom::Point3d.new(Float(args["origin"][0]).mm, Float(args["origin"][1]).mm, Float(args["origin"][2]).mm)
    else
      combined_bb.center
    end

    t = Geom::Transformation.scaling(origin_pt, x_scale, y_scale, z_scale)

    with_operation(model, "AI - Scale Entities") do
      entities.each do |entity|
        if entity.respond_to?(:transform!)
          entity.transform!(t)
        elsif entity.parent && entity.parent.respond_to?(:entities)
          entity.parent.entities.transform_entities(t, [entity])
        else
          model.active_entities.transform_entities(t, [entity])
        end
      end
      bump_model_revision
    end

    {
      ok: true,
      operation: "scale",
      scaled_count: entities.length,
      missing_ids: missing_ids,
      scale: [x_scale, y_scale, z_scale],
      origin_mm: [origin_pt.x.to_mm.round(1), origin_pt.y.to_mm.round(1), origin_pt.z.to_mm.round(1)],
      entities: entities.map { |e| entity_metadata(e) },
      bounds_mm: calculate_bounds_mm(entities),
      model_revision: model_revision,
      mcp_revision: model_revision
    }
  end

  def delete_entities(args)
    model = Sketchup.active_model
    raise "Không có model nào đang mở" unless model

    entities, missing_ids = resolve_entities_from_args(model, args)
    raise ArgumentError, "Không tìm thấy đối tượng nào hợp lệ để xóa" if entities.empty?

    deleted_items = []
    with_operation(model, "AI - Delete Entities") do
      entities.each do |entity|
        meta = entity_metadata(entity)
        if entity.respond_to?(:erase!)
          entity.erase!
          deleted_items << meta
        end
      end
      bump_model_revision
    end

    {
      ok: true,
      operation: "delete",
      deleted_count: deleted_items.length,
      missing_ids: missing_ids,
      entities: deleted_items,
      model_revision: model_revision,
      mcp_revision: model_revision
    }
  end

  def group_entities(args)
    model = Sketchup.active_model
    raise "Không có model nào đang mở" unless model

    name = args["name"].to_s
    entities, missing_ids = resolve_entities_from_args(model, args)
    raise ArgumentError, "Cần ít nhất một đối tượng hợp lệ để tạo nhóm" if entities.empty?

    # Verify all entities share the same parent container
    parents = entities.map { |e| e.respond_to?(:parent) ? e.parent : nil }.uniq
    if parents.length > 1
      parent_names = parents.map { |p| p.is_a?(Sketchup::Model) ? "Model root" : (p.respond_to?(:name) ? p.name : p.class.name) }
      raise ArgumentError, "Tất cả đối tượng phải cùng chung một container mới nhóm được. Hiện có #{parents.length} containers khác nhau: #{parent_names.join(', ')}"
    end

    # Use the parent's entities collection, not necessarily model.active_entities
    target_entities_collection = if parents.first.is_a?(Sketchup::Model)
      parents.first.active_entities
    elsif parents.first.respond_to?(:entities)
      parents.first.entities
    else
      model.active_entities
    end

    group = nil
    with_operation(model, "AI - Group Entities") do
      group = target_entities_collection.add_group(entities)
      group.name = name unless name.empty?
      bump_model_revision
    end

    {
      ok: true,
      operation: "group",
      group: entity_metadata(group),
      children_count: entities.length,
      missing_ids: missing_ids,
      bounds_mm: group.bounds ? {
        width: group.bounds.width.to_mm.round(1),
        depth: group.bounds.height.to_mm.round(1),
        height: group.bounds.depth.to_mm.round(1),
        center: [group.bounds.center.x.to_mm.round(1), group.bounds.center.y.to_mm.round(1), group.bounds.center.z.to_mm.round(1)]
      } : nil,
      model_revision: model_revision,
      mcp_revision: model_revision
    }
  end

  def ungroup_entities(args)
    model = Sketchup.active_model
    raise "Không có model nào đang mở" unless model

    target = args["id"] || args["persistent_id"] || args["entity_id"]
    raise ArgumentError, "Thiếu tham số id/persistent_id của group cần rã" unless target

    entity = find_entity(model, target)
    raise ArgumentError, "Không tìm thấy group với ID cung cấp" unless entity && entity.valid?
    raise ArgumentError, "Đối tượng ID #{target} không phải là Sketchup::Group (loại: #{entity.class.name})" unless entity.is_a?(Sketchup::Group)

    exploded_entities = []
    with_operation(model, "AI - Ungroup Entities") do
      exploded_entities = entity.explode
      bump_model_revision
    end

    {
      ok: true,
      operation: "ungroup",
      exploded_count: exploded_entities.length,
      model_revision: model_revision,
      mcp_revision: model_revision
    }
  end

  # ==========================================
  # Dispatch API Handlers - Materials & Attributes
  # ==========================================

  def create_material(args)
    model = Sketchup.active_model
    raise "Không có model nào đang mở" unless model

    name = (args["name"] || args["material_name"]).to_s.strip
    raise ArgumentError, "Tên vật liệu không được để trống" if name.empty?

    mat = model.materials[name]
    created_new = mat.nil?

    with_operation(model, "AI - Create/Update Material") do
      mat ||= model.materials.add(name)

      # Handle color
      if args["color"]
        c_arg = args["color"]
        if c_arg.is_a?(Array) && c_arg.length >= 3
          mat.color = Sketchup::Color.new(c_arg[0].to_i, c_arg[1].to_i, c_arg[2].to_i, (c_arg[3] || 255).to_i)
        elsif c_arg.is_a?(String) && !c_arg.strip.empty?
          mat.color = Sketchup::Color.new(c_arg.strip)
        end
      end

      # Handle alpha
      if args.key?("alpha")
        alpha_val = Float(args["alpha"]).clamp(0.0, 1.0)
        mat.alpha = alpha_val
      end

      # Handle texture
      if args["texture_path"] && !args["texture_path"].to_s.strip.empty?
        tex_path = args["texture_path"].to_s.strip
        if File.exist?(tex_path)
          mat.texture = tex_path
          tex = mat.texture
          if tex
            tex.width = Float(args["texture_width"]).mm if args["texture_width"]
            tex.height = Float(args["texture_height"]).mm if args["texture_height"]
          end
        else
          raise ArgumentError, "File texture không tồn tại: #{tex_path}"
        end
      end

      bump_model_revision
    end

    {
      ok: true,
      operation: "create_material",
      created_new: created_new,
      material: material_metadata(mat),
      model_revision: model_revision,
      mcp_revision: model_revision,
      protocol_version: PROTOCOL_VERSION,
      min_compatible_protocol_version: MIN_COMPATIBLE_PROTOCOL_VERSION
    }
  end

  def set_entity_material(args)
    model = Sketchup.active_model
    raise "Không có model nào đang mở" unless model

    mat_name = (args["material_name"] || args["name"]).to_s.strip
    raise ArgumentError, "Thiếu tham số tên vật liệu (material_name)" if mat_name.empty?

    mat = model.materials[mat_name]
    raise ArgumentError, "Vật liệu '#{mat_name}' chưa tồn tại trong model" unless mat

    entities, missing_ids = resolve_entities_from_args(model, args)
    raise ArgumentError, "Không tìm thấy đối tượng nào hợp lệ để gán vật liệu" if entities.empty?

    entities.each do |e|
      validate_group_or_component!(e)
    end

    with_operation(model, "AI - Set Entity Material") do
      entities.each do |e|
        e.material = mat
      end
      bump_model_revision
    end

    {
      ok: true,
      operation: "set_entity_material",
      updated_count: entities.length,
      material_name: mat_name,
      missing_ids: missing_ids,
      entities: entities.map { |e| entity_metadata(e) },
      model_revision: model_revision,
      mcp_revision: model_revision,
      protocol_version: PROTOCOL_VERSION,
      min_compatible_protocol_version: MIN_COMPATIBLE_PROTOCOL_VERSION
    }
  end

  def clear_entity_material(args)
    model = Sketchup.active_model
    raise "Không có model nào đang mở" unless model

    entities, missing_ids = resolve_entities_from_args(model, args)
    raise ArgumentError, "Không tìm thấy đối tượng nào hợp lệ để xóa vật liệu" if entities.empty?

    entities.each do |e|
      validate_group_or_component!(e)
    end

    with_operation(model, "AI - Clear Entity Material") do
      entities.each do |e|
        e.material = nil
      end
      bump_model_revision
    end

    {
      ok: true,
      operation: "clear_entity_material",
      cleared_count: entities.length,
      missing_ids: missing_ids,
      entities: entities.map { |e| entity_metadata(e) },
      model_revision: model_revision,
      mcp_revision: model_revision,
      protocol_version: PROTOCOL_VERSION,
      min_compatible_protocol_version: MIN_COMPATIBLE_PROTOCOL_VERSION
    }
  end

  def set_entity_attributes(args)
    model = Sketchup.active_model
    raise "Không có model nào đang mở" unless model

    dict_name = args["dictionary_name"].to_s.strip
    raise ArgumentError, "Thiếu tham số dictionary_name" if dict_name.empty?

    attrs = args["attributes"]
    raise ArgumentError, "attributes phải là một Hash key-value" unless attrs.is_a?(Hash) && !attrs.empty?

    entities, missing_ids = resolve_entities_from_args(model, args)
    raise ArgumentError, "Không tìm thấy đối tượng nào hợp lệ để gán thuộc tính" if entities.empty?

    entities.each do |e|
      validate_group_or_component!(e)
    end

    with_operation(model, "AI - Set Entity Attributes") do
      entities.each do |e|
        attrs.each do |k, v|
          e.set_attribute(dict_name, k.to_s, v)
        end
      end
      bump_model_revision
    end

    {
      ok: true,
      operation: "set_entity_attributes",
      updated_count: entities.length,
      dictionary_name: dict_name,
      attributes_written: attrs.keys,
      missing_ids: missing_ids,
      entities: entities.map { |e| entity_metadata(e) },
      model_revision: model_revision,
      mcp_revision: model_revision,
      protocol_version: PROTOCOL_VERSION,
      min_compatible_protocol_version: MIN_COMPATIBLE_PROTOCOL_VERSION
    }
  end

  def delete_entity_attributes(args)
    model = Sketchup.active_model
    raise "Không có model nào đang mở" unless model

    dict_name = args["dictionary_name"].to_s.strip
    raise ArgumentError, "Thiếu tham số dictionary_name" if dict_name.empty?

    keys = args["keys"].is_a?(Array) ? args["keys"].map(&:to_s) : nil

    entities, missing_ids = resolve_entities_from_args(model, args)
    raise ArgumentError, "Không tìm thấy đối tượng nào hợp lệ để xóa thuộc tính" if entities.empty?

    entities.each do |e|
      validate_group_or_component!(e)
    end

    with_operation(model, "AI - Delete Entity Attributes") do
      entities.each do |e|
        if keys && !keys.empty?
          dict = e.attribute_dictionary(dict_name, false)
          if dict
            keys.each { |k| dict.delete_key(k) }
          end
        elsif e.attribute_dictionaries
          e.attribute_dictionaries.delete(dict_name)
        end
      end
      bump_model_revision
    end

    {
      ok: true,
      operation: "delete_entity_attributes",
      updated_count: entities.length,
      dictionary_name: dict_name,
      deleted_keys: keys,
      deleted_entire_dictionary: keys.nil? || keys.empty?,
      missing_ids: missing_ids,
      model_revision: model_revision,
      mcp_revision: model_revision,
      protocol_version: PROTOCOL_VERSION,
      min_compatible_protocol_version: MIN_COMPATIBLE_PROTOCOL_VERSION
    }
  end

  # ==========================================
  # Dispatch API Handlers - Components & Assembly (v1.2)
  # ==========================================

  def create_component(args)
    model = Sketchup.active_model
    raise "Không có model nào đang mở" unless model

    name = (args["name"] || args["component_name"]).to_s.strip
    raise ArgumentError, "Tên component không được để trống" if name.empty?

    entities, missing_ids = resolve_entities_from_args(model, args)
    raise ArgumentError, "Không tìm thấy đối tượng nào hợp lệ để tạo component" if entities.empty?

    description = args["description"].to_s

    instance = nil
    definition = nil

    with_operation(model, "AI - Create Component") do
      if entities.length == 1 && entities.first.is_a?(Sketchup::Group)
        instance = entities.first.to_component
      else
        temp_group = model.active_entities.add_group(entities)
        instance = temp_group.to_component
      end
      definition = instance.definition
      definition.name = name
      definition.description = description unless description.empty?
      bump_model_revision
    end

    {
      ok: true,
      operation: "create_component",
      definition: {
        name: definition.name,
        guid: definition.guid,
        instances_count: definition.instances.length,
        description: definition.description
      },
      instance: entity_metadata(instance),
      missing_ids: missing_ids,
      model_revision: model_revision,
      mcp_revision: model_revision,
      protocol_version: PROTOCOL_VERSION,
      min_compatible_protocol_version: MIN_COMPATIBLE_PROTOCOL_VERSION
    }
  end

  def get_component_definitions(args)
    model = Sketchup.active_model
    raise "Không có model nào đang mở" unless model

    include_internal = args["include_internal"] == true
    name_filter = args["name_filter"].to_s.downcase.strip

    items = []
    model.definitions.each do |defn|
      next if !include_internal && defn.group?
      next if !name_filter.empty? && !defn.name.downcase.include?(name_filter)

      bbox = defn.bounds
      items << {
        name: defn.name,
        guid: defn.guid,
        instances_count: defn.instances.length,
        description: defn.description,
        is_group_internal: defn.group?,
        bounds_mm: bbox ? {
          width: bbox.width.to_mm.round(1),
          depth: bbox.height.to_mm.round(1),
          height: bbox.depth.to_mm.round(1)
        } : nil
      }
    end

    {
      ok: true,
      total_count: items.length,
      definitions: items,
      protocol_version: PROTOCOL_VERSION,
      min_compatible_protocol_version: MIN_COMPATIBLE_PROTOCOL_VERSION
    }
  end

  def place_component_instance(args)
    model = Sketchup.active_model
    raise "Không có model nào đang mở" unless model

    name = (args["definition_name"] || args["name"]).to_s.strip
    raise ArgumentError, "Thiếu tham số definition_name" if name.empty?

    defn = model.definitions[name]
    raise ArgumentError, "Không tìm thấy ComponentDefinition có tên '#{name}' trong model" unless defn

    container = model.active_entities
    if args["parent_id"]
      parent_entity = find_entity_by_persistent_id(model, args["parent_id"]) || find_entity_by_id(model, args["parent_id"])
      raise ArgumentError, "Không tìm thấy parent entity với ID #{args['parent_id']}" unless parent_entity
      if parent_entity.is_a?(Sketchup::Group)
        container = parent_entity.entities
      elsif parent_entity.is_a?(Sketchup::ComponentInstance)
        container = parent_entity.definition.entities
      else
        raise ArgumentError, "Parent entity phải là Group hoặc ComponentInstance"
      end
    end

    transform = build_transformation(args)
    inst_name = args["instance_name"].to_s.strip

    instance = nil
    with_operation(model, "AI - Place Component Instance") do
      instance = container.add_instance(defn, transform)
      instance.name = inst_name unless inst_name.empty?
      bump_model_revision
    end

    bbox = instance.bounds
    {
      ok: true,
      operation: "place_component_instance",
      definition_name: defn.name,
      instance: entity_metadata(instance),
      position_mm: [bbox.center.x.to_mm.round(1), bbox.center.y.to_mm.round(1), bbox.center.z.to_mm.round(1)],
      bounds_mm: {
        width: bbox.width.to_mm.round(1),
        depth: bbox.height.to_mm.round(1),
        height: bbox.depth.to_mm.round(1)
      },
      model_revision: model_revision,
      mcp_revision: model_revision,
      protocol_version: PROTOCOL_VERSION,
      min_compatible_protocol_version: MIN_COMPATIBLE_PROTOCOL_VERSION
    }
  end

  def make_component_unique(args)
    model = Sketchup.active_model
    raise "Không có model nào đang mở" unless model

    entities, missing_ids = resolve_entities_from_args(model, args)
    raise ArgumentError, "Không tìm thấy instance nào để make_unique" if entities.empty?

    components = entities.select { |e| e.is_a?(Sketchup::ComponentInstance) }
    raise ArgumentError, "Không có ComponentInstance nào trong danh sách được cung cấp" if components.empty?

    new_name = args["new_name"].to_s.strip

    with_operation(model, "AI - Make Component Unique") do
      components.each do |comp|
        comp.make_unique
        comp.definition.name = new_name if !new_name.empty? && components.length == 1
      end
      bump_model_revision
    end

    {
      ok: true,
      operation: "make_component_unique",
      updated_count: components.length,
      new_definition_name: components.first.definition.name,
      missing_ids: missing_ids,
      model_revision: model_revision,
      mcp_revision: model_revision,
      protocol_version: PROTOCOL_VERSION,
      min_compatible_protocol_version: MIN_COMPATIBLE_PROTOCOL_VERSION
    }
  end

  def save_component_to_skp(args)
    model = Sketchup.active_model
    raise "Không có model nào đang mở" unless model

    name = (args["definition_name"] || args["name"]).to_s.strip
    raise ArgumentError, "Thiếu tham số definition_name" if name.empty?

    defn = model.definitions[name]
    raise ArgumentError, "Không tìm thấy definition '#{name}' trong model" unless defn

    file_path = args["file_path"].to_s.strip
    raise ArgumentError, "Thiếu tham số file_path" if file_path.empty?
    raise ArgumentError, "Đường dẫn file phải có đuôi .skp" unless file_path.downcase.end_with?(".skp")

    dir = File.dirname(file_path)
    raise ArgumentError, "Thư mục không tồn tại: #{dir}" unless Dir.exist?(dir)

    overwrite = args["overwrite"] == true
    if File.exist?(file_path) && !overwrite
      raise ArgumentError, "File '#{file_path}' đã tồn tại (dùng overwrite: true nếu muốn ghi đè)"
    end

    success = defn.save_as(file_path)
    raise "Lỗi lưu definition ra file .skp" unless success

    {
      ok: true,
      operation: "save_component_to_skp",
      definition_name: defn.name,
      file_path: file_path,
      file_size_bytes: File.size(file_path),
      protocol_version: PROTOCOL_VERSION,
      min_compatible_protocol_version: MIN_COMPATIBLE_PROTOCOL_VERSION
    }
  end

  def load_component_from_skp(args)
    model = Sketchup.active_model
    raise "Không có model nào đang mở" unless model

    file_path = args["file_path"].to_s.strip
    raise ArgumentError, "Thiếu tham số file_path" if file_path.empty?
    raise ArgumentError, "File không tồn tại: #{file_path}" unless File.exist?(file_path)
    raise ArgumentError, "File phải có định dạng .skp" unless file_path.downcase.end_with?(".skp")

    defn = nil
    with_operation(model, "AI - Load Component From SKP") do
      defn = model.definitions.load(file_path)
      if args["definition_name"] && !args["definition_name"].to_s.strip.empty?
        defn.name = args["definition_name"].to_s.strip
      end
      bump_model_revision
    end

    bbox = defn.bounds
    {
      ok: true,
      operation: "load_component_from_skp",
      definition: {
        name: defn.name,
        guid: defn.guid,
        instances_count: defn.instances.length,
        bounds_mm: bbox ? {
          width: bbox.width.to_mm.round(1),
          depth: bbox.height.to_mm.round(1),
          height: bbox.depth.to_mm.round(1)
        } : nil
      },
      model_revision: model_revision,
      mcp_revision: model_revision,
      protocol_version: PROTOCOL_VERSION,
      min_compatible_protocol_version: MIN_COMPATIBLE_PROTOCOL_VERSION
    }
  end

  # ==========================================
  # Dispatch Router & Metrics
  # ==========================================

  def elapsed_ms(started_at)
    ((Process.clock_gettime(Process::CLOCK_MONOTONIC) - started_at) * 1000).round(2)
  end

  def response_error(request_id, command, code, message, error_class = nil)
    {
      ok: false,
      request_id: request_id,
      command: command,
      error: {
        code: code,
        message: message,
        class: error_class
      }
    }
  end

  def dispatch(payload)
    request_id = payload["request_id"].to_s
    command = payload["command"].to_s
    started_at = Process.clock_gettime(Process::CLOCK_MONOTONIC)

    unless payload["token"].to_s == TOKEN
      return response_error(request_id, command, "UNAUTHORIZED", "Invalid token")
    end

    args = payload["arguments"]
    args = {} unless args.is_a?(Hash)

    result = case command
    when "ping"
      ping_response
    when "toggle_dev_mode"
      response_error(request_id, command, "FORBIDDEN", "Dev mode chỉ được bật/tắt trực tiếp từ menu SketchUp hoặc biến môi trường")
    when "model_summary"
      model_summary
    when "get_selection"
      get_selection
    when "get_entities"
      get_entities(args)
    when "get_entity_info"
      get_entity_info(args)
    when "get_bounding_box"
      get_bounding_box(args)
    when "execute_ruby"
      execute_ruby(args)
    when "create_box"
      create_box(args)
    when "create_cylinder"
      create_cylinder(args)
    when "create_wall"
      create_wall(args)
    when "capture_viewport"
      capture_viewport(args)
    when "zoom_extents"
      zoom_extents
    when "move"
      move_entities(args)
    when "copy"
      copy_entities(args)
    when "rotate"
      rotate_entities(args)
    when "scale"
      scale_entities(args)
    when "delete"
      delete_entities(args)
    when "group"
      group_entities(args)
    when "ungroup"
      ungroup_entities(args)
    when "get_materials"
      get_materials(args)
    when "get_material_info"
      get_material_info(args)
    when "create_material"
      create_material(args)
    when "set_entity_material"
      set_entity_material(args)
    when "clear_entity_material"
      clear_entity_material(args)
    when "get_entity_attributes"
      get_entity_attributes(args)
    when "set_entity_attributes"
      set_entity_attributes(args)
    when "delete_entity_attributes"
      delete_entity_attributes(args)
    when "create_component"
      create_component(args)
    when "get_component_definitions"
      get_component_definitions(args)
    when "place_component_instance"
      place_component_instance(args)
    when "make_component_unique"
      make_component_unique(args)
    when "save_component_to_skp"
      save_component_to_skp(args)
    when "load_component_from_skp"
      load_component_from_skp(args)
    when "reload_extension"
      response_error(request_id, command, "FORBIDDEN", "Reload extension chỉ được thực hiện trực tiếp từ menu SketchUp")
    else
      response_error(request_id, command, "UNKNOWN_COMMAND", "Unknown command: #{command}")
    end

    result = {
      ok: false,
      error: {
        code: "INVALID_HANDLER_RESPONSE",
        message: "Command handler không trả về Hash"
      }
    } unless result.is_a?(Hash)

    if result[:ok] == false && result[:error].is_a?(String)
      result[:error] = {
        code: "HANDLER_ERROR",
        message: result[:error],
        class: result[:error_class]
      }
      result.delete(:error_class)
    end

    result.merge(
      request_id: request_id,
      command: command,
      duration_ms: elapsed_ms(started_at)
    )
  rescue StandardError => e
    response_error(request_id, command, "INTERNAL_ERROR", e.message, e.class.name)
  end

  # ==========================================
  # Non-blocking Main Thread Socket Polling
  # ==========================================

  def write_response(socket, payload)
    body = JSON.generate(payload)
    socket.write("#{body.bytesize}\n")
    socket.write(body)
    socket.flush
  end

  def handle_client(client)
    set_socket_timeout(client, 5)

    length_line = client.gets
    return unless length_line

    length = Integer(length_line.strip)
    raise "Invalid request length: #{length}" if length <= 0 || length > 5_000_000

    body = client.read(length)
    raise "Incomplete request body" unless body && body.bytesize == length

    payload = JSON.parse(body)
    result = dispatch(payload)
    write_response(client, result)
  rescue JSON::ParserError => e
    write_response(client, { ok: false, error: { code: "INVALID_JSON", message: e.message, class: e.class.name } }) rescue nil
  rescue StandardError => e
    write_response(client, { ok: false, error: { code: "CLIENT_ERROR", message: e.message, class: e.class.name } }) rescue nil
  ensure
    client.close rescue nil
  end

  def poll_server(max_clients = 2)
    return unless @server && !@server.closed?

    processed = 0
    while processed < max_clients
      begin
        client = @server.accept_nonblock
        processed += 1
        handle_client(client)
      rescue IO::WaitReadable, Errno::EAGAIN, Errno::EWOULDBLOCK
        break
      rescue StandardError => error
        puts "TuSketchupAgent poll error: #{error.message}"
        break
      end
    end
  end

  def start_server(silent = false)
    stop_server(true) rescue nil

    @server = nil
    @started = false

    server = TCPServer.new(HOST, PORT)
    @server = server
    @started = true

    @timer_id = UI.start_timer(0.05, true) do
      poll_server(2)
    end

    UI.messagebox("TCP bridge đang chạy tại #{HOST}:#{PORT}") unless silent
    puts "TuSketchupAgent: TCP bridge started successfully at #{HOST}:#{PORT} (Main Thread Polling)"
  rescue StandardError => error
    @server.close rescue nil if @server
    @server = nil
    @started = false
    UI.messagebox("Không thể khởi động bridge: #{error.message}") unless silent
    puts "TuSketchupAgent error starting server: #{error.message}"
  end

  def stop_server(silent = false)
    if @timer_id
      UI.stop_timer(@timer_id) rescue nil
      @timer_id = nil
    end

    cleanup_resources

    UI.messagebox("TCP bridge đã dừng.") unless silent
    puts "TuSketchupAgent: TCP bridge stopped."
  rescue => error
    UI.messagebox("Lỗi khi dừng bridge: #{error.message}") unless silent
  end

  def reload_extension
    stop_server(true)
    load __FILE__
    puts "TuSketchupAgent: Extension reloaded from #{__FILE__}"
  end

  # ==========================================
  # SketchUp Menu & Auto-start
  # ==========================================

  unless file_loaded?(__FILE__)
    menu = UI.menu("Extensions")
    submenu = menu.add_submenu("Tu SketchUp Agent")

    submenu.add_item("Ping / Status") { ping }
    submenu.add_item("Toggle Dev Mode") do
      @dev_mode = !@dev_mode
      UI.messagebox("Chế độ Dev Mode: #{@dev_mode ? 'BẬT (Cho phép execute_ruby)' : 'TẮT (Chặn execute_ruby)'}")
    end
    submenu.add_separator
    submenu.add_item("Create Test Box (1000mm)") do
      create_box("width" => 1000, "depth" => 1000, "height" => 1000, "name" => "Test Box")
      UI.messagebox("Đã tạo khối hộp 1000 x 1000 x 1000 mm.")
    end
    submenu.add_separator
    submenu.add_item("Start TCP Bridge") { start_server }
    submenu.add_item("Stop TCP Bridge") { stop_server }
    submenu.add_separator
    submenu.add_item("Reload Extension") { reload_extension }

    file_loaded(__FILE__)
  end

  # Khởi động bridge polling sau khi load
  UI.start_timer(0.3, false) do
    start_server(true) rescue nil
  end
end