(() => {
  "use strict";

  const NATIVE_HOST_NAME = "youtube_discord_rpc";
  let port = null;
  let currentState = { connected: false, playing: false, data: null };
  let reconnectDelay = 5000;
  const MAX_RECONNECT_DELAY = 60000;

  function connectNativeHost() {
    if (port) return;

    try {
      port = chrome.runtime.connectNative(NATIVE_HOST_NAME);

      port.onMessage.addListener((message) => {
        reconnectDelay = 5000; // reset backoff on successful message
        if (message.type === "CONNECTED") {
          currentState.connected = true;
        } else if (message.type === "DISCONNECTED") {
          currentState.connected = false;
        } else if (message.type === "ERROR") {
          console.error("[SyncView] Error:", message.error);
          currentState.connected = false;
        }
      });

      port.onDisconnect.addListener(() => {
        const lastError = chrome.runtime.lastError?.message || "";
        port = null;
        currentState.connected = false;

        if (lastError.includes("not found")) {
          console.warn("[SyncView] Native host not found. Run SyncView.exe to register it. Will retry in", reconnectDelay / 1000, "s");
        } else {
          console.warn("[SyncView] Native host disconnected:", lastError);
        }

        // Exponential backoff to avoid spamming
        setTimeout(() => connectNativeHost(), reconnectDelay);
        reconnectDelay = Math.min(reconnectDelay * 2, MAX_RECONNECT_DELAY);
      });
    } catch (e) {
      console.error("[SyncView] Failed to connect native host:", e);
      port = null;
      currentState.connected = false;
    }
  }

  function sendToNativeHost(message) {
    if (!port) {
      connectNativeHost();
    }
    if (port) {
      try {
        port.postMessage(message);
      } catch (e) {
        console.error("[SyncView] Failed to send message:", e);
        port = null;
      }
    }
  }

  // Listen for messages from the content script
  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type === "MEDIA_PLAYING") {
      const { data } = message;
      currentState.playing = true;
      currentState.data = data;

      // activityType: 2 = Listening, 3 = Watching
      const isListening = data.activityType === 2;

      const activity = {
        type: data.activityType,
        details: data.title.substring(0, 128),
        state: data.channel
          ? (isListening ? `by ${data.channel}` : `${data.channel}`).substring(0, 128)
          : data.siteName,
      };

      // Timestamps
      if (!data.paused && data.duration > 0 && !data.isLive) {
        const nowSec = Math.floor(Date.now() / 1000);
        const remaining = data.duration - data.currentTime;
        activity.timestamps = { end: nowSec + remaining };
      }

      if (data.isLive) {
        activity.state = data.channel
          ? `${data.channel} - LIVE`.substring(0, 128)
          : "LIVE";
        activity.timestamps = { start: Math.floor(Date.now() / 1000) };
      }

      // Assets: thumbnail as large image
      if (data.thumbnailUrl) {
        activity.assets = {
          large_image: data.thumbnailUrl,
          large_text: data.title.substring(0, 128),
        };
      }

      // Buttons: link to content + Sync View website (visible to others, not yourself)
      const actionLabel = isListening ? `Listen on ${data.siteName}` : `Watch on ${data.siteName}`;
      activity.buttons = [];
      if (data.url) {
        activity.buttons.push({ label: actionLabel, url: data.url.substring(0, 512) });
      }
      activity.buttons.push({ label: "Get Sync View", url: "https://syncview.app/" });

      sendToNativeHost({ type: "SET_ACTIVITY", activity });

    } else if (message.type === "MEDIA_IDLE") {
      currentState.playing = false;
      currentState.data = null;
      sendToNativeHost({ type: "CLEAR_ACTIVITY" });
    } else if (message.type === "GET_STATE") {
      sendResponse(currentState);
      return true; // keep channel open for sendResponse
    }
  });

  connectNativeHost();
})();
