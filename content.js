(() => {
  "use strict";

  // ── Site Definitions ──────────────────────────────────────────────────────
  // Each site defines how to extract playback metadata from the DOM.
  // activityType: 2 = Listening, 3 = Watching

  const SITES = {
    youtube: {
      name: "YouTube",
      hostname: "www.youtube.com",
      activityType: 3,
      watchPattern: /\/watch/,
      getData() {
        const video = document.querySelector("video");
        if (!video || !video.src) return null;

        const title =
          document.querySelector("ytd-watch-metadata #title yt-formatted-string")?.textContent?.trim() ||
          document.querySelector("#above-the-fold #title yt-formatted-string")?.textContent?.trim() ||
          document.querySelector("h1.ytd-watch-metadata yt-formatted-string")?.textContent?.trim() ||
          document.querySelector("#info-contents h1 yt-formatted-string")?.textContent?.trim() ||
          document.querySelector('meta[name="title"]')?.content?.trim() ||
          document.title.replace(" - YouTube", "").trim();

        const channel =
          document.querySelector("ytd-watch-metadata ytd-channel-name yt-formatted-string a")?.textContent?.trim() ||
          document.querySelector("#above-the-fold ytd-channel-name a")?.textContent?.trim() ||
          document.querySelector("#owner #channel-name a")?.textContent?.trim() ||
          document.querySelector("ytd-channel-name a")?.textContent?.trim() || "";

        const liveBadge = document.querySelector(".ytp-live-badge");
        const isLive = liveBadge ? !liveBadge.hasAttribute("disabled") : false;

        const urlParams = new URLSearchParams(window.location.search);
        const videoId = urlParams.get("v") || "";

        if (!title || title === "YouTube") return null;

        return {
          title, channel, videoId, isLive,
          currentTime: Math.floor(video.currentTime || 0),
          duration: Math.floor(video.duration || 0),
          paused: video.paused,
          thumbnailUrl: videoId ? `https://i.ytimg.com/vi/${videoId}/hqdefault.jpg` : "",
          url: window.location.href,
        };
      },
    },

    youtubeMusic: {
      name: "YouTube Music",
      hostname: "music.youtube.com",
      activityType: 2,
      watchPattern: /./,
      getData() {
        const video = document.querySelector("video");
        if (!video) return null;

        // Try Media Session API first (YouTube Music populates it reliably)
        const meta = navigator.mediaSession?.metadata;
        const title = meta?.title ||
          document.querySelector("ytmusic-player-bar .title")?.textContent?.trim() ||
          document.querySelector(".content-info-wrapper .title")?.textContent?.trim() || "";
        const channel = meta?.artist ||
          document.querySelector("ytmusic-player-bar .byline a")?.textContent?.trim() ||
          document.querySelector(".content-info-wrapper .byline a")?.textContent?.trim() || "";
        const artwork = meta?.artwork?.[0]?.src || "";

        if (!title) return null;

        return {
          title, channel, isLive: false,
          currentTime: Math.floor(video.currentTime || 0),
          duration: Math.floor(video.duration || 0),
          paused: video.paused,
          thumbnailUrl: artwork,
          url: window.location.href,
        };
      },
    },

    netflix: {
      name: "Netflix",
      hostname: "www.netflix.com",
      activityType: 3,
      watchPattern: /\/watch\//,
      getData() {
        const video = document.querySelector("video");
        if (!video) return null;

        // Netflix populates Media Session API
        const meta = navigator.mediaSession?.metadata;
        const title = meta?.title ||
          document.querySelector(".video-title h4")?.textContent?.trim() ||
          document.title.replace(" - Netflix", "").trim();
        const channel = meta?.artist || meta?.album || "";
        const artwork = meta?.artwork?.[0]?.src || "";

        if (!title || title === "Netflix") return null;

        return {
          title, channel, isLive: false,
          currentTime: Math.floor(video.currentTime || 0),
          duration: Math.floor(video.duration || 0),
          paused: video.paused,
          thumbnailUrl: artwork,
          url: window.location.href,
        };
      },
    },

    spotify: {
      name: "Spotify",
      hostname: "open.spotify.com",
      activityType: 2,
      watchPattern: /./,
      getData() {
        // Spotify Web Player: use data-testid selectors + Media Session
        const meta = navigator.mediaSession?.metadata;
        const title = meta?.title ||
          document.querySelector('[data-testid="context-item-link"]')?.textContent?.trim() ||
          document.querySelector('[data-testid="nowplaying-track-link"]')?.textContent?.trim() || "";
        const channel = meta?.artist ||
          document.querySelector('[data-testid="context-item-info-artist"]')?.textContent?.trim() ||
          document.querySelector('[data-testid="track-info-artists"]')?.textContent?.trim() || "";
        const artwork = meta?.artwork?.[0]?.src || "";

        const playBtn = document.querySelector('[data-testid="control-button-playpause"]');
        const paused = playBtn ? playBtn.getAttribute("aria-label")?.toLowerCase()?.includes("play") : true;

        const currentTimeText = document.querySelector('[data-testid="playback-position"]')?.textContent || "0:00";
        const durationText = document.querySelector('[data-testid="playback-duration"]')?.textContent || "0:00";

        if (!title) return null;

        return {
          title, channel, isLive: false,
          currentTime: parseTimeString(currentTimeText),
          duration: parseTimeString(durationText),
          paused,
          thumbnailUrl: artwork,
          url: window.location.href,
        };
      },
    },

    twitch: {
      name: "Twitch",
      hostname: "www.twitch.tv",
      activityType: 3,
      watchPattern: /^\/[^/]+\/?$/,
      getData() {
        const video = document.querySelector("video");
        if (!video) return null;

        const title = document.querySelector('p[data-a-target="stream-title"]')?.textContent?.trim() || "";
        const channel = document.querySelector(".channel-info-content h1")?.textContent?.trim() ||
          document.querySelector('[data-a-target="stream-title"]')
            ?.closest("[class]")
            ?.parentElement
            ?.querySelector("h1")?.textContent?.trim() || "";
        const game = document.querySelector('a[data-a-target="stream-game-link"]')?.textContent?.trim() || "";

        // Twitch uses a very large duration for live streams
        const isLive = !isFinite(video.duration) || video.duration > 1000000000;

        if (!title && !channel) return null;

        return {
          title: title || `${channel}'s stream`,
          channel: game ? `${channel} — ${game}` : channel,
          isLive,
          currentTime: 0,
          duration: 0,
          paused: video.paused,
          thumbnailUrl: "",
          url: window.location.href,
        };
      },
    },

    hulu: {
      name: "Hulu",
      hostname: "www.hulu.com",
      activityType: 3,
      watchPattern: /\/watch\//,
      getData() {
        const video = document.querySelector("video");
        if (!video) return null;

        const meta = navigator.mediaSession?.metadata;
        const title = meta?.title ||
          document.querySelector(".PlayerMetadata__titleText")?.textContent?.trim() ||
          document.title.replace(" - Hulu", "").trim();
        const channel = meta?.artist || meta?.album ||
          document.querySelector(".PlayerMetadata__subTitle")?.textContent?.trim() || "";
        const artwork = meta?.artwork?.[0]?.src || "";

        if (!title || title === "Hulu") return null;

        return {
          title, channel, isLive: false,
          currentTime: Math.floor(video.currentTime || 0),
          duration: Math.floor(video.duration || 0),
          paused: video.paused,
          thumbnailUrl: artwork,
          url: window.location.href,
        };
      },
    },

    disneyPlus: {
      name: "Disney+",
      hostname: "www.disneyplus.com",
      activityType: 3,
      watchPattern: /\/video\//,
      getData() {
        const video = document.querySelector("video");
        if (!video) return null;

        const meta = navigator.mediaSession?.metadata;
        const title = meta?.title ||
          document.querySelector('[data-testid="details-title-treatment"] img')?.alt?.trim() ||
          document.title.replace("| Disney+", "").trim();
        const channel = meta?.artist || meta?.album ||
          document.querySelector(".subtitle-text")?.textContent?.trim() || "";
        const artwork = meta?.artwork?.[0]?.src || "";

        if (!title || title === "Disney+") return null;

        return {
          title, channel, isLive: false,
          currentTime: Math.floor(video.currentTime || 0),
          duration: Math.floor(video.duration || 0),
          paused: video.paused,
          thumbnailUrl: artwork,
          url: window.location.href,
        };
      },
    },

    primeVideo: {
      name: "Prime Video",
      hostname: "www.primevideo.com",
      activityType: 3,
      watchPattern: /\/detail\/|\/watch/,
      getData() {
        const video = document.querySelector("video");
        if (!video) return null;

        const meta = navigator.mediaSession?.metadata;
        const title = meta?.title ||
          document.querySelector(".atvwebplayersdk-subtitle-text")?.textContent?.trim() ||
          document.title.replace("Prime Video", "").replace("|", "").trim();
        const channel = meta?.artist || meta?.album || "";
        const artwork = meta?.artwork?.[0]?.src || "";

        if (!title || title === "Prime Video") return null;

        return {
          title, channel, isLive: false,
          currentTime: Math.floor(video.currentTime || 0),
          duration: Math.floor(video.duration || 0),
          paused: video.paused,
          thumbnailUrl: artwork,
          url: window.location.href,
        };
      },
    },

    soundcloud: {
      name: "SoundCloud",
      hostname: "soundcloud.com",
      activityType: 2,
      watchPattern: /./,
      getData() {
        const isPlaying = !!document.querySelector(".playControls__play.playing");
        const title = document.querySelector(".playbackSoundBadge__titleLink > span:nth-child(2)")?.textContent?.trim() || "";
        const channel = document.querySelector(".playbackSoundBadge__lightLink")?.textContent?.trim() || "";

        const currentTimeText = document.querySelector("div.playbackTimeline__timePassed > span:nth-child(2)")?.textContent || "0:00";
        const durationText = document.querySelector("div.playbackTimeline__duration > span:nth-child(2)")?.textContent || "0:00";

        const thumbEl = document.querySelector(".playbackSoundBadge__avatar.sc-media-image > div > span");
        const thumbStyle = thumbEl?.style?.backgroundImage || "";
        const thumbnailUrl = thumbStyle.replace(/url\(["']?/, "").replace(/["']?\)/, "");

        if (!title) return null;

        return {
          title, channel, isLive: false,
          currentTime: parseTimeString(currentTimeText),
          duration: parseTimeString(durationText),
          paused: !isPlaying,
          thumbnailUrl,
          url: window.location.href,
        };
      },
    },

    crunchyroll: {
      name: "Crunchyroll",
      hostname: "www.crunchyroll.com",
      activityType: 3,
      watchPattern: /\/watch\//,
      getData() {
        const video = document.querySelector("video");
        if (!video) return null;

        const meta = navigator.mediaSession?.metadata;
        const title = meta?.title ||
          document.querySelector("h1.title")?.textContent?.trim() ||
          document.querySelector("a > h4")?.textContent?.trim() ||
          document.title.replace("- Crunchyroll", "").trim();
        const channel = meta?.artist || meta?.album || "";
        const artwork = meta?.artwork?.[0]?.src ||
          document.querySelector('[property="og:image"]')?.content || "";

        if (!title || title === "Crunchyroll") return null;

        return {
          title, channel, isLive: false,
          currentTime: Math.floor(video.currentTime || 0),
          duration: Math.floor(video.duration || 0),
          paused: video.paused,
          thumbnailUrl: artwork,
          url: window.location.href,
        };
      },
    },

    max: {
      name: "Max",
      hostname: "www.max.com",
      activityType: 3,
      watchPattern: /\/video\/watch/,
      getData() {
        const video = document.querySelector("video");
        if (!video) return null;

        const meta = navigator.mediaSession?.metadata;
        const title = meta?.title ||
          document.title.replace("| Max", "").trim();
        const channel = meta?.artist || meta?.album || "";
        const artwork = meta?.artwork?.[0]?.src || "";

        if (!title || title === "Max") return null;

        return {
          title, channel, isLive: false,
          currentTime: Math.floor(video.currentTime || 0),
          duration: Math.floor(video.duration || 0),
          paused: video.paused,
          thumbnailUrl: artwork,
          url: window.location.href,
        };
      },
    },

    appleTv: {
      name: "Apple TV+",
      hostname: "tv.apple.com",
      activityType: 3,
      watchPattern: /\/(watch|episode)\//,
      getData() {
        const video = document.querySelector("video");
        if (!video) return null;

        const meta = navigator.mediaSession?.metadata;
        const title = meta?.title ||
          document.querySelector(".video-metadata .title")?.textContent?.trim() ||
          document.title.replace("| Apple TV+", "").trim();
        const channel = meta?.artist || meta?.album ||
          document.querySelector(".video-metadata .subtitle-text")?.textContent?.trim() || "";
        const artwork = meta?.artwork?.[0]?.src || "";

        if (!title || title === "Apple TV+") return null;

        return {
          title, channel, isLive: false,
          currentTime: Math.floor(video.currentTime || 0),
          duration: Math.floor(video.duration || 0),
          paused: video.paused,
          thumbnailUrl: artwork,
          url: window.location.href,
        };
      },
    },

    plex: {
      name: "Plex",
      hostname: "app.plex.tv",
      activityType: 3,
      watchPattern: /./,
      getData() {
        const video = document.querySelector("video");
        if (!video || !video.src) return null;

        // Plex populates Media Session API when playing content
        const meta = navigator.mediaSession?.metadata;
        const title = meta?.title ||
          document.querySelector('[class*="MetadataPosterTitle"] a')?.textContent?.trim() ||
          document.querySelector('[data-testid="metadata-title"]')?.textContent?.trim() ||
          document.querySelector('[class*="PlayerControlsMetadata"] [class*="Title"]')?.textContent?.trim() ||
          document.title.replace("▶ ", "").replace(" - Plex", "").trim();

        const channel = meta?.artist || meta?.album ||
          document.querySelector('[class*="MetadataPosterTitle"] span[class*="MetadataYear"]')?.textContent?.trim() ||
          document.querySelector('[data-testid="metadata-subtitle"]')?.textContent?.trim() ||
          document.querySelector('[class*="PlayerControlsMetadata"] [class*="Subtitle"]')?.textContent?.trim() || "";

        const artwork = meta?.artwork?.[0]?.src || "";

        // Plex live TV detection
        const isLive = !!document.querySelector('[class*="LiveBadge"]') ||
          window.location.href.includes("/livetv/");

        if (!title || title === "Plex") return null;

        // Determine if this is music (Listening) or video (Watching)
        const isMusicSection = window.location.href.includes("/music/") ||
          document.querySelector('[class*="AudioPlayer"]') !== null;

        return {
          title, channel, isLive,
          currentTime: Math.floor(video.currentTime || 0),
          duration: Math.floor(video.duration || 0),
          paused: video.paused,
          thumbnailUrl: artwork,
          url: window.location.href,
          activityTypeOverride: isMusicSection ? 2 : undefined,
        };
      },
    },
  };

  // ── Helpers ───────────────────────────────────────────────────────────────

  function parseTimeString(str) {
    if (!str) return 0;
    const parts = str.split(":").map(Number);
    if (parts.length === 3) return parts[0] * 3600 + parts[1] * 60 + parts[2];
    if (parts.length === 2) return parts[0] * 60 + parts[1];
    return parts[0] || 0;
  }

  function detectSite() {
    const host = window.location.hostname.replace(/^m\./, "");
    // YouTube Music must be checked before YouTube (subdomain match)
    if (host === "music.youtube.com") return SITES.youtubeMusic;
    if (host.includes("youtube.com")) return SITES.youtube;
    if (host.includes("netflix.com")) return SITES.netflix;
    if (host.includes("spotify.com")) return SITES.spotify;
    if (host.includes("twitch.tv")) return SITES.twitch;
    if (host.includes("hulu.com")) return SITES.hulu;
    if (host.includes("disneyplus.com")) return SITES.disneyPlus;
    if (host.includes("primevideo.com") || (host.includes("amazon.com") && window.location.pathname.includes("/gp/video"))) return SITES.primeVideo;
    if (host.includes("soundcloud.com")) return SITES.soundcloud;
    if (host.includes("crunchyroll.com")) return SITES.crunchyroll;
    if (host.includes("max.com")) return SITES.max;
    if (host === "tv.apple.com") return SITES.appleTv;
    if (host.includes("plex.tv")) return SITES.plex;
    return null;
  }

  // ── Main Logic ────────────────────────────────────────────────────────────

  const site = detectSite();
  if (!site) return;

  let lastSentData = null;
  let pollInterval = null;

  function dataChanged(newData) {
    if (!lastSentData || !newData) return true;
    return (
      lastSentData.title !== newData.title ||
      lastSentData.paused !== newData.paused ||
      lastSentData.isLive !== newData.isLive ||
      Math.abs(lastSentData.currentTime - newData.currentTime) > 5
    );
  }

  function sendUpdate() {
    const data = site.getData();
    if (!data) {
      if (lastSentData) {
        browser.runtime.sendMessage({ type: "MEDIA_IDLE" });
        lastSentData = null;
      }
      return;
    }

    if (dataChanged(data)) {
      browser.runtime.sendMessage({
        type: "MEDIA_PLAYING",
        data: {
          ...data,
          siteName: site.name,
          activityType: data.activityTypeOverride || site.activityType,
        },
      });
      lastSentData = { ...data };
    }
  }

  function startPolling() {
    if (pollInterval) return;
    pollInterval = setInterval(sendUpdate, 3000);
    setTimeout(sendUpdate, 500);
  }

  function stopPolling() {
    if (pollInterval) {
      clearInterval(pollInterval);
      pollInterval = null;
    }
    browser.runtime.sendMessage({ type: "MEDIA_IDLE" });
    lastSentData = null;
  }

  // SPA navigation detection
  let lastUrl = window.location.href;
  const observer = new MutationObserver(() => {
    if (window.location.href !== lastUrl) {
      lastUrl = window.location.href;
      lastSentData = null;
      setTimeout(sendUpdate, 3000);
    }
  });
  observer.observe(document.body, { childList: true, subtree: true });

  // Start polling (with delay for SPA content to load)
  setTimeout(startPolling, 3000);

  // Listen for video play/pause events globally
  document.addEventListener("playing", () => startPolling(), true);
  document.addEventListener("pause", () => sendUpdate(), true);

  window.addEventListener("beforeunload", () => {
    stopPolling();
    observer.disconnect();
  });
})();
