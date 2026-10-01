import XCTest

final class LaunchTests: XCTestCase {
    func testBundledGameStartsAndResumes() {
        let app = XCUIApplication()
        app.launch()
        let start = app.webViews.buttons["Bấm để bắt đầu"]
        XCTAssertTrue(start.waitForExistence(timeout: 60))
        start.tap()
        XCTAssertTrue(app.webViews["game-ready"].waitForExistence(timeout: 120), "Python game must draw its first frame from bundled resources")
        let attachment = XCTAttachment(screenshot: app.screenshot())
        attachment.lifetime = .keepAlways
        add(attachment)
        XCUIDevice.shared.press(.home)
        app.activate()
        XCTAssertTrue(app.webViews["game-ready"].exists)
    }
}
