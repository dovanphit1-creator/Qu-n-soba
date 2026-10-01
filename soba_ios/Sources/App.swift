import UIKit
import WebKit
import AVFoundation

@main
final class AppDelegate: UIResponder, UIApplicationDelegate {
    var window: UIWindow?
    func application(_ application: UIApplication, didFinishLaunchingWithOptions options: [UIApplication.LaunchOptionsKey: Any]?) -> Bool {
        let window = UIWindow(frame: UIScreen.main.bounds)
        window.rootViewController = GameController()
        window.makeKeyAndVisible(); self.window = window
        return true
    }
    func applicationWillResignActive(_ application: UIApplication) {
        (window?.rootViewController as? GameController)?.saveBeforeBackground()
    }
}

final class GameController: UIViewController, WKScriptMessageHandler, WKNavigationDelegate {
    private var web: WKWebView!
    private var server: LocalServer?
    private var store: SaveStore?
    private let speech = AVSpeechSynthesizer()
    override var supportedInterfaceOrientations: UIInterfaceOrientationMask { .landscape }
    override var prefersStatusBarHidden: Bool { true }
    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = UIColor(red: 0.15, green: 0.22, blue: 0.18, alpha: 1)
        do {
            let store = try SaveStore(); self.store = store
            let configuration = WKWebViewConfiguration()
            configuration.websiteDataStore = .nonPersistent()
            configuration.allowsInlineMediaPlayback = true
            configuration.mediaTypesRequiringUserActionForPlayback = []
            let bridge = try String(contentsOf: Bundle.main.url(forResource: "bridge", withExtension: "js")!, encoding: .utf8)
            let initial = try store.initialBase64()
            configuration.userContentController.addUserScript(WKUserScript(
                source: "window.sobaIOSInitialSave = '\(initial)';\n" + bridge,
                injectionTime: .atDocumentStart, forMainFrameOnly: true))
            configuration.userContentController.add(self, name: "game")
            web = WKWebView(frame: .zero, configuration: configuration)
            web.navigationDelegate = self
            web.scrollView.isScrollEnabled = false
            web.scrollView.bounces = false
            web.isOpaque = false
            web.translatesAutoresizingMaskIntoConstraints = false
            view.addSubview(web)
            NSLayoutConstraint.activate([
                web.leadingAnchor.constraint(equalTo: view.safeAreaLayoutGuide.leadingAnchor),
                web.trailingAnchor.constraint(equalTo: view.safeAreaLayoutGuide.trailingAnchor),
                web.topAnchor.constraint(equalTo: view.safeAreaLayoutGuide.topAnchor),
                web.bottomAnchor.constraint(equalTo: view.safeAreaLayoutGuide.bottomAnchor)])
            guard let root = Bundle.main.url(forResource: "Game", withExtension: nil) else {
                throw CocoaError(.fileNoSuchFile)
            }
            let server = LocalServer(root: root); self.server = server
            try server.start { [weak self] result in
                DispatchQueue.main.async {
                    switch result {
                    case .success(let url): self?.web.load(URLRequest(url: url))
                    case .failure(let error): self?.showFailure(error)
                    }
                }
            }
        } catch { showFailure(error) }
    }
    private func showFailure(_ error: Error) {
        let alert = UIAlertController(title: "Chưa mở được game", message: "Dữ liệu lưu vẫn được giữ nguyên.\n\(error.localizedDescription)", preferredStyle: .alert)
        alert.addAction(UIAlertAction(title: "Đóng", style: .cancel))
        present(alert, animated: true)
    }
    private func command(_ object: [String: String]) {
        guard let data = try? JSONSerialization.data(withJSONObject: object), let json = String(data: data, encoding: .utf8) else { return }
        web.evaluateJavaScript("window.sobaIOSCommands.push(\(json))", completionHandler: nil)
    }
    func saveBeforeBackground() {
        guard web != nil else { return }
        // Give the JS/Python bridge time to flush its final atomic native save.
        var task: UIBackgroundTaskIdentifier = .invalid
        task = UIApplication.shared.beginBackgroundTask {
            if task != .invalid { UIApplication.shared.endBackgroundTask(task); task = .invalid }
        }
        command(["kind":"save"])
        DispatchQueue.main.asyncAfter(deadline: .now() + 2) {
            if task != .invalid { UIApplication.shared.endBackgroundTask(task); task = .invalid }
        }
        speech.stopSpeaking(at: .immediate)
    }
    func userContentController(_ controller: WKUserContentController, didReceive message: WKScriptMessage) {
        guard message.frameInfo.isMainFrame, message.frameInfo.securityOrigin.host == "127.0.0.1",
              let body = message.body as? [String: Any], let kind = body["kind"] as? String else { return }
        switch kind {
        case "ready":
            web.accessibilityIdentifier = "game-ready"
        case "reload":
            webViewWebContentProcessDidTerminate(web)
        case "save":
            guard let snapshot = body["snapshot"] as? String, let backups = body["backups"] as? [String: String] else { return }
            do { try store?.write(snapshot: snapshot, backups: backups) }
            catch { command(["kind":"saveError"]) }
        case "speak":
            guard let text = body["text"] as? String else { return }
            let utterance = AVSpeechUtterance(string: text)
            utterance.voice = AVSpeechSynthesisVoice(language: "vi-VN")
            utterance.rate = 0.47
            speech.speak(utterance)
        case "text":
            guard presentedViewController == nil, let field = body["field"] as? String,
                  let value = body["value"] as? String else { return }
            let titles = ["name":"Tên món ăn", "price":"Giá bán (VND)", "shift_name":"Tên ca làm"]
            guard let title = titles[field] else { return }
            let alert = UIAlertController(title: title, message: nil, preferredStyle: .alert)
            alert.addTextField { input in
                input.text = value
                input.keyboardType = field == "price" ? .numberPad : .default
            }
            alert.addAction(UIAlertAction(title: "Hủy", style: .cancel) { [weak self] _ in self?.command(["kind":"cancelText"]) })
            alert.addAction(UIAlertAction(title: "Xong", style: .default) { [weak self, weak alert] _ in
                self?.command(["kind":"text", "field":field, "text":alert?.textFields?.first?.text ?? ""])
            })
            present(alert, animated: true)
        default: break
        }
    }
    func webView(_ webView: WKWebView, decidePolicyFor action: WKNavigationAction, decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
        guard let url = action.request.url else { decisionHandler(.cancel); return }
        decisionHandler(url.host == "127.0.0.1" || url.scheme == "about" ? .allow : .cancel)
    }
    func webViewWebContentProcessDidTerminate(_ webView: WKWebView) {
        // Reconstruct the initial bridge from the latest on-disk save on recovery.
        webView.configuration.userContentController.removeScriptMessageHandler(forName: "game")
        webView.removeFromSuperview()
        viewDidLoad()
    }
}
