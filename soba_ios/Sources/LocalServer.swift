import Foundation
import Network

/// Loopback-only origin for the bundled WebAssembly runtime. Never exposes files to Wi-Fi.
final class LocalServer {
    private let root: URL
    private var listener: NWListener?
    private let queue = DispatchQueue(label: "quanmi.local-assets")
    init(root: URL) { self.root = root.standardizedFileURL }
    func start(completion: @escaping (Result<URL, Error>) -> Void) throws {
        let parameters = NWParameters.tcp
        parameters.requiredLocalEndpoint = .hostPort(host: "127.0.0.1", port: .any)
        let listener = try NWListener(using: parameters)
        self.listener = listener
        listener.stateUpdateHandler = { state in
            switch state {
            case .ready:
                if let port = listener.port { completion(.success(URL(string: "http://127.0.0.1:\(port)/index.html")!)) }
            case .failed(let error): completion(.failure(error))
            default: break
            }
        }
        listener.newConnectionHandler = { [weak self] connection in
            guard let self else { connection.cancel(); return }
            connection.start(queue: self.queue)
            self.receive(connection, buffer: Data())
        }
        listener.start(queue: queue)
    }
    private func receive(_ connection: NWConnection, buffer: Data) {
        connection.receive(minimumIncompleteLength: 1, maximumLength: 16384) { [weak self] data, _, complete, error in
            guard let self, error == nil, let data else { connection.cancel(); return }
            var buffer = buffer; buffer.append(data)
            guard buffer.count <= 32768 else { connection.cancel(); return }
            if let request = String(data: buffer, encoding: .utf8), request.contains("\r\n\r\n") {
                self.respond(connection, request: request)
            } else if !complete { self.receive(connection, buffer: buffer) }
            else { connection.cancel() }
        }
    }
    static func resolve(_ requestPath: String, root: URL) -> URL? {
        guard let path = requestPath.split(separator: "?", maxSplits: 1).first.map(String.init)?.removingPercentEncoding,
              !path.contains("\0"), !path.contains("\\") else { return nil }
        let file = root.appendingPathComponent(path == "/" ? "index.html" : String(path.drop(while: { $0 == "/" }))).standardizedFileURL
        return file.path.hasPrefix(root.standardizedFileURL.path + "/") ? file : nil
    }
    private func respond(_ connection: NWConnection, request: String) {
        let parts = request.components(separatedBy: "\r\n")[0].split(separator: " ")
        var status = "404 Not Found", body = Data(), mime = "text/plain"
        if parts.count >= 2, parts[0] == "GET", let file = Self.resolve(String(parts[1]), root: root),
           let bytes = try? Data(contentsOf: file) {
            status = "200 OK"; body = bytes
            mime = ["html":"text/html; charset=utf-8", "js":"application/javascript", "wasm":"application/wasm",
                    "json":"application/json", "css":"text/css", "png":"image/png", "ogg":"audio/ogg",
                    "wav":"audio/wav", "gz":"application/gzip" ][file.pathExtension] ?? "application/octet-stream"
        }
        let header = "HTTP/1.1 \(status)\r\nContent-Type: \(mime)\r\nContent-Length: \(body.count)\r\nCache-Control: no-store\r\nConnection: close\r\n\r\n"
        var response = Data(header.utf8); response.append(body)
        connection.send(content: response, completion: .contentProcessed { _ in connection.cancel() })
    }
    deinit { listener?.cancel() }
}
