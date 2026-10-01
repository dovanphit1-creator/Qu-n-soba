import Foundation

/// Save bytes live in Application Support, independent of WebKit's website cache.
final class SaveStore {
    let directory: URL
    var file: URL { directory.appendingPathComponent("save-vnd.json") }
    init(directory: URL? = nil) throws {
        self.directory = try directory ?? FileManager.default.url(for: .applicationSupportDirectory,
            in: .userDomainMask, appropriateFor: nil, create: true).appendingPathComponent("QuanMiCuaToi")
        try FileManager.default.createDirectory(at: self.directory, withIntermediateDirectories: true)
    }
    func initialBase64() throws -> String {
        guard FileManager.default.fileExists(atPath: file.path) else { return "" }
        return try Data(contentsOf: file).base64EncodedString()
    }
    func write(snapshot: String, backups: [String: String]) throws {
        let data = Data(snapshot.utf8)
        guard let object = try JSONSerialization.jsonObject(with: data) as? [String: Any],
              object["version"] as? Int == 10 else { throw CocoaError(.fileWriteInapplicableStringEncoding) }
        // Write all recovery copies before replacing the current save.
        for (name, encoded) in backups {
            guard name.hasPrefix("save-vnd."), name.hasSuffix(".bak"),
                  !name.contains("/"), !name.contains("\\"), let bytes = Data(base64Encoded: encoded)
            else { throw CocoaError(.fileWriteInvalidFileName) }
            let backup = directory.appendingPathComponent(name)
            if !FileManager.default.fileExists(atPath: backup.path) { try bytes.write(to: backup, options: .atomic) }
        }
        try data.write(to: file, options: .atomic)
    }
}
