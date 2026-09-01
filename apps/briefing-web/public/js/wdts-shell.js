(function () {
  "use strict";

  function escapeHtml(value) {
    return String(value).replace(/[&<>"']/g, function (char) {
      return ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
      })[char];
    });
  }

  function sanitizeUrl(value, fallback) {
    var url = String(value || "").trim();
    var safeFallback = fallback || "/";
    if (!url) return safeFallback;
    if (/^https?:\/\//i.test(url)) return url;
    if (/^\/\//.test(url)) return safeFallback;
    if (/^[a-zA-Z][a-zA-Z0-9+.-]*:/.test(url)) return safeFallback;
    return url;
  }

  function renderHeader(config) {
    var brandHref = escapeHtml(sanitizeUrl(config.brandHref, "/"));
    var brandTitleRaw = config.brandTitle || "Walker Digital";
    var brandTitle = escapeHtml(brandTitleRaw);
    var brandSubtitle = escapeHtml(config.brandSubtitle || "AI Apps Directory");
    var logoSrc = escapeHtml(sanitizeUrl(config.logoSrc, "/images/brand/logo-wdts-48x52.png"));
    var brandAriaLabel = escapeHtml(config.brandAriaLabel || (brandTitleRaw + " home"));
    var pickerClass = config.showThemeTokenPicker ? "theme-prefs" : "theme-prefs hide";
    var showUserLoginDetails = config.showUserLoginDetails === true;
    var userPillHtml = showUserLoginDetails
      ? '<div class="user-pill" id="user-pill" hidden>' +
      '<button type="button" class="user-pill__trigger" id="user-pill-trigger" aria-haspopup="menu" aria-expanded="false" aria-controls="user-menu">' +
      '<span class="user-pill__avatar" id="user-pill-avatar" aria-hidden="true">·</span>' +
      '<span class="user-pill__name" id="user-pill-name">Signed in</span>' +
      '<span class="user-pill__chevron" aria-hidden="true">▾</span>' +
      "</button>" +
      '<div class="user-menu" id="user-menu" role="menu" aria-labelledby="user-pill-trigger" hidden>' +
      '<div class="user-menu__header"><div class="user-menu__name" id="user-menu-name"></div>' +
      '<div class="user-menu__email" id="user-menu-email"></div></div>' +
      '<a class="user-menu__item" href="/logout" role="menuitem"><span class="ico" aria-hidden="true">↗</span>Sign out</a>' +
      "</div></div>"
      : "";

    var showBrandLogo = config.showBrandLogo !== false;
    var logoHtml = showBrandLogo
      ? '<span class="portal__logo" aria-hidden="true"><img src="' + logoSrc + '" alt=""></span>'
      : "";

    return '<header class="portal__header">' +
      '<div class="portal__header-start">' +
      '<a class="portal__brand" href="' + brandHref + '" aria-label="' + brandAriaLabel + '">' +
      logoHtml +
      '<span class="portal__brand-text">' +
      '<span class="portal__title" id="portal-title" translate="no">' + brandTitle + "</span>" +
      '<span class="portal__subtitle" id="portal-subtitle">' + brandSubtitle + "</span>" +
      "</span></a></div>" +
      '<div class="portal__header-actions">' +
      '<div class="' + pickerClass + '" id="theme-prefs">' +
      '<select id="brand-token-select" class="theme-prefs__select" aria-label="Theme">' +
      '<option value="teal">Teal</option>' +
      '<option value="deep-red">Deep Red</option>' +
      '<option value="orange">Orange</option>' +
      '<option value="gold">Gold</option>' +
      '<option value="purple">Purple</option>' +
      '<option value="charcoal">Charcoal</option>' +
      "</select></div>" +
      '<button type="button" class="theme-toggle" id="theme-toggle" aria-label="Toggle colour theme" title="Toggle theme" aria-pressed="false">' +
      '<svg class="theme-toggle__moon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">' +
      '<path d="M20.5 14.5A8 8 0 1 1 9.5 3.5a6.5 6.5 0 0 0 11 11z"></path>' +
      "</svg>" +
      '<svg class="theme-toggle__sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">' +
      '<circle cx="12" cy="12" r="4"></circle><path d="M12 2v2"></path><path d="M12 20v2"></path>' +
      '<path d="M4.93 4.93l1.41 1.41"></path><path d="M17.66 17.66l1.41 1.41"></path><path d="M2 12h2"></path>' +
      '<path d="M20 12h2"></path><path d="M4.93 19.07l1.41-1.41"></path><path d="M17.66 6.34l1.41-1.41"></path>' +
      "</svg></button>" +
      userPillHtml +
      "</div></header>";
  }

  function renderFooter(config) {
    var footerText = escapeHtml(config.footerText || "");
    return '<footer class="portal__footer">' +
      '<span class="portal__footer-text">' + footerText + "</span>" +
      "</footer>";
  }

  function mount(config) {
    var options = config || {};
    var headerHost = document.getElementById(options.headerHostId || "wdts-shell-header");
    var footerHost = document.getElementById(options.footerHostId || "wdts-shell-footer");

    if (headerHost) headerHost.outerHTML = renderHeader(options);
    if (footerHost) footerHost.outerHTML = renderFooter(options);
  }

  window.WDTSShell = { mount: mount };
})();
