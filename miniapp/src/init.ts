import {
  backButton,
  init as initSdk,
  mainButton,
  miniApp,
  themeParams,
  viewport,
} from "@tma.js/sdk-react";

export function initTelegram(): void {
  initSdk();

  if (miniApp.mount.isAvailable()) {
    miniApp.mount();
    if (miniApp.ready.isAvailable()) {
      miniApp.ready();
    }
  }

  if (themeParams.mount.isAvailable()) {
    themeParams.mount();
    if (themeParams.bindCssVars.isAvailable()) {
      themeParams.bindCssVars();
    }
  }

  if (viewport.mount.isAvailable()) {
    void viewport.mount().then(() => {
      if (viewport.bindCssVars.isAvailable()) {
        viewport.bindCssVars();
      }
      if (viewport.expand.isAvailable()) {
        viewport.expand();
      }
    });
  }

  if (mainButton.mount.isAvailable()) {
    mainButton.mount();
  }

  if (backButton.mount.isAvailable()) {
    backButton.mount();
  }
}
