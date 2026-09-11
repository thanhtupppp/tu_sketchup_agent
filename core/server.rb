# frozen_string_literal: true

require "socket"

module TuSketchupAgent
  module Server
    extend self

    @server = nil
    @timer_id = nil
    @started = false
    @managed_threads = []

    def running?
      @started && !@server.nil? && !@server.closed?
    end

    def cleanup_resources
      @managed_threads.each do |thread|
        thread.kill if thread.alive? rescue nil
      end
      @managed_threads.clear

      if @server && !@server.closed?
        @server.close rescue nil
      end

      # Cleanup legacy server socket from parent TuSketchupAgent module if present
      if TuSketchupAgent.instance_variable_defined?(:@server)
        legacy_server = TuSketchupAgent.instance_variable_get(:@server)
        legacy_server.close rescue nil if legacy_server && !legacy_server.closed?
        TuSketchupAgent.instance_variable_set(:@server, nil)
      end
      if TuSketchupAgent.instance_variable_defined?(:@timer_id)
        legacy_timer = TuSketchupAgent.instance_variable_get(:@timer_id)
        UI.stop_timer(legacy_timer) rescue nil if legacy_timer
        TuSketchupAgent.instance_variable_set(:@timer_id, nil)
      end
    rescue StandardError => e
      puts "TuSketchupAgent cleanup error: #{e.message}"
    ensure
      @server = nil
      @started = false
    end

    def set_socket_timeout(socket, seconds = 5)
      if Gem.win_platform? || RUBY_PLATFORM =~ /mswin|mingw|cygwin/
        timeout_ms = (seconds * 1000).to_i
        socket.setsockopt(Socket::SOL_SOCKET, Socket::SO_RCVTIMEO, [timeout_ms].pack("i"))
        socket.setsockopt(Socket::SOL_SOCKET, Socket::SO_SNDTIMEO, [timeout_ms].pack("i"))
      else
        timeval = [seconds.to_i, 0].pack("l_2")
        socket.setsockopt(Socket::SOL_SOCKET, Socket::SO_RCVTIMEO, timeval)
        socket.setsockopt(Socket::SOL_SOCKET, Socket::SO_SNDTIMEO, timeval)
      end
    rescue StandardError => e
      puts "TuSketchupAgent socket timeout warning: #{e.message}"
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
      result = Router.dispatch(payload)
      Response.write(client, result)
    rescue JSON::ParserError => e
      Response.write(client, { ok: false, error: { code: "INVALID_JSON", message: e.message, class: e.class.name } }) rescue nil
    rescue StandardError => e
      Response.write(client, { ok: false, error: { code: "CLIENT_ERROR", message: e.message, class: e.class.name } }) rescue nil
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

    def start(silent = false)
      stop(true) rescue nil

      @server = nil
      @started = false

      retries = 3
      begin
        server = TCPServer.new(TuSketchupAgent::HOST, TuSketchupAgent::PORT)
      rescue Errno::EADDRINUSE => err
        retries -= 1
        if retries > 0
          sleep(0.1)
          retry
        else
          raise err
        end
      end

      @server = server
      @started = true

      @timer_id = UI.start_timer(0.05, true) do
        begin
          poll_server(2)
        rescue Exception => e
          puts "TuSketchupAgent timer critical error: #{e.class.name}: #{e.message}"
        end
      end

      UI.messagebox("TCP bridge đang chạy tại #{TuSketchupAgent::HOST}:#{TuSketchupAgent::PORT}") unless silent
      puts "TuSketchupAgent: TCP bridge started successfully at #{TuSketchupAgent::HOST}:#{TuSketchupAgent::PORT} (Main Thread Polling)"
    rescue StandardError => error
      @server.close rescue nil if @server
      @server = nil
      @started = false
      UI.messagebox("Không thể khởi động bridge: #{error.message}") unless silent
      puts "TuSketchupAgent error starting server: #{error.message}"
    end

    def stop(silent = false)
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
  end

  # Module-level delegates for backward compatibility
  def self.running?
    Server.running?
  end

  def self.start_server(silent = false)
    Server.start(silent)
  end

  def self.stop_server(silent = false)
    Server.stop(silent)
  end

  def self.cleanup_resources
    Server.cleanup_resources
  end

  def self.set_socket_timeout(socket, seconds = 5)
    Server.set_socket_timeout(socket, seconds)
  end

  def self.poll_server(max_clients = 2)
    Server.poll_server(max_clients)
  end

  def self.handle_client(client)
    Server.handle_client(client)
  end
end
