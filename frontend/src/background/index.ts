console.log("Background service worker running");

chrome.runtime.onInstalled.addListener(() => {
    chrome.contextMenus.create({
        id: "verify-claim",
        title: "Verify Claim",
        contexts: ["selection"],
    });
});

chrome.contextMenus.onClicked.addListener((info: chrome.contextMenus.OnClickData, tab?: chrome.tabs.Tab) => {
    if (info.menuItemId === "verify-claim" && tab?.id) {
        // Open the side panel
        chrome.sidePanel.open({ tabId: tab.id });

        // Send message to side panel
        // We might need a small delay or retry mechanism if side panel is not yet open
        setTimeout(() => {
            chrome.runtime.sendMessage({
                type: "VERIFY_CLAIM",
                payload: {
                    text: info.selectionText,
                    url: tab.url,
                    title: tab.title,
                    tabId: tab.id
                }
            }).catch((err: any) => console.log("Side panel not ready yet", err));
        }, 500);
    }
});
