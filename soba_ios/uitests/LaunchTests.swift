import XCTest

final class LaunchTests: XCTestCase {
    func testBundledGameStartsAndResumes() {
        let app = XCUIApplication()
        app.launch()
        let start = app.webViews.buttons["Bấm để bắt đầu"]
        XCTAssertTrue(start.waitForExistence(timeout: 60))
        start.tap()
        XCTAssertTrue(app.webViews["game-ready"].waitForExistence(timeout: 120), "Python game must draw its first frame from bundled resources")
        app.webViews["game-ready"].coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.794)).tap()
        let zoom = app.webViews.buttons["Phóng to"]
        XCTAssertTrue(zoom.waitForExistence(timeout: 5))
        zoom.tap()
        app.webViews.buttons["Xem toàn quán"].tap()
        let attachment = XCTAttachment(screenshot: app.screenshot())
        attachment.lifetime = .keepAlways
        add(attachment)
        XCUIDevice.shared.press(.home)
        app.activate()
        XCTAssertTrue(app.webViews["game-ready"].exists)
        app.terminate()
        app.launch()
        XCTAssertTrue(start.waitForExistence(timeout: 60))
        start.tap()
        XCTAssertTrue(app.webViews["game-ready"].waitForExistence(timeout: 120))
    }
}
