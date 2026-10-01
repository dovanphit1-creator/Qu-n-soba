// Injected by the native controller before any bundled game code runs.
window.sobaIOSCommands = [];
window.sobaIOSDrain = () => JSON.stringify(window.sobaIOSCommands.splice(0));
window.sobaIOSSave = (snapshot, backups) => window.webkit.messageHandlers.game.postMessage({kind:'save', snapshot, backups:JSON.parse(backups)});
window.sobaIOSEdit = (field, value) => window.webkit.messageHandlers.game.postMessage({kind:'text', field, value});
window.sobaSpeak = text => window.webkit.messageHandlers.game.postMessage({kind:'speak', text});
document.addEventListener('visibilitychange', () => {
  if (document.hidden) window.sobaIOSCommands.push({kind:'save'});
});
