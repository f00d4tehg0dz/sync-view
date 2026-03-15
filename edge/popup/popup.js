(() => {
  "use strict";

  function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  }

  async function updatePopup() {
    try {
      const state = await chrome.runtime.sendMessage({ type: "GET_STATE" });

      const statusEl = document.getElementById("status");
      const statusText = document.getElementById("status-text");
      const nowPlaying = document.getElementById("now-playing");
      const idleMessage = document.getElementById("idle-message");

      if (state.connected) {
        statusEl.className = "status connected";
        statusText.textContent = "Connected to Discord";
      } else {
        statusEl.className = "status disconnected";
        statusText.textContent = "Disconnected";
      }

      if (state.playing && state.data) {
        const { data } = state;
        nowPlaying.classList.remove("hidden");
        idleMessage.classList.add("hidden");

        document.getElementById("site-badge").textContent = data.siteName || "";
        document.getElementById("title").textContent = data.title;
        document.getElementById("channel").textContent = data.channel || "";

        const thumb = document.getElementById("thumbnail");
        if (data.thumbnailUrl) {
          thumb.src = data.thumbnailUrl;
          thumb.style.display = "block";
        } else {
          thumb.style.display = "none";
        }

        if (data.isLive) {
          document.getElementById("progress").textContent = "LIVE";
        } else if (data.paused) {
          document.getElementById("progress").textContent =
            `Paused at ${formatTime(data.currentTime)}`;
        } else if (data.duration > 0) {
          document.getElementById("progress").textContent =
            `${formatTime(data.currentTime)} / ${formatTime(data.duration)}`;
        } else {
          document.getElementById("progress").textContent = "";
        }
      } else {
        nowPlaying.classList.add("hidden");
        idleMessage.classList.remove("hidden");
      }
    } catch (e) {
      console.error("Failed to get state:", e);
    }
  }

  updatePopup();
  setInterval(updatePopup, 3000);
})();
