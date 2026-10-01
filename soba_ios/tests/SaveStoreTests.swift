import XCTest
@testable import QuanMiCuaToi

final class SaveStoreTests: XCTestCase {
    func testAtomicSaveAndRecoveryBackup() throws {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: root) }
        let store = try SaveStore(directory: root)
        XCTAssertEqual(try store.initialBase64(), "")
        let original = Data("broken save".utf8)
        try original.write(to: store.file)
        let good = "{\"version\":10,\"money\":10000000}"
        try store.write(snapshot: good, backups: ["save-vnd.json.123.bak":original.base64EncodedString()])
        XCTAssertEqual(try Data(contentsOf: root.appendingPathComponent("save-vnd.json.123.bak")), original)
        XCTAssertEqual(try String(contentsOf: store.file), good)
        XCTAssertThrowsError(try store.write(snapshot: "broken", backups: [:]))
        XCTAssertEqual(try String(contentsOf: store.file), good)
    }
    func testPathTraversalIsRejected() {
        let root = URL(fileURLWithPath: "/bundle/Game")
        XCTAssertNil(LocalServer.resolve("/../secret", root: root))
        XCTAssertNil(LocalServer.resolve("/%2e%2e/secret", root: root))
        XCTAssertEqual(LocalServer.resolve("/runtime/main.wasm?x=1", root: root)?.path, "/bundle/Game/runtime/main.wasm")
    }
}
