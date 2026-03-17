# Session token not working: postMessage origin mismatch

## What you're seeing

- **"[Tryon session] FAIL: App Bridge getSessionToken not ready after 60 attempts"**
- **"Failed to execute 'postMessage' on 'DOMWindow': The target origin provided ('https://tryon.global') does not match the recipient window's origin ('https://admin.shopify.com')."**

## What’s going on

1. **Embed flow**  
   Shopify loads `https://tryon.global/app?shop=...&host=...` in an iframe inside `admin.shopify.com`.

2. **App Bridge**  
   The App Bridge script (from Shopify’s CDN) runs on that page and must talk to the **parent** (admin) via `postMessage` to get a session token.

3. **postMessage error**  
   Something is calling `postMessage(..., 'https://tryon.global')` when the **recipient** is the parent window, whose origin is `https://admin.shopify.com`. The second argument must be the **recipient’s** origin, so it should be `'https://admin.shopify.com'`, not `'https://tryon.global'`. The browser blocks the call and the handshake never completes.

4. **Result**  
   Because that handshake fails, `window.shopify.getSessionToken` never becomes ready, so we hit “getSessionToken not ready after 60 attempts”.

So: **session token isn’t working because the postMessage handshake with the admin is failing due to the wrong target origin.**

## Likely cause

- The wrong-origin `postMessage` is almost certainly from **Shopify’s own script** (e.g. App Bridge or admin’s `common-*.js`), not from our app code (we don’t call `postMessage` on `/app`).
- Known causes from Shopify’s side include:
  - **Host param**  
    App Bridge is supposed to get the parent’s origin from the `host` query param (base64 of e.g. `admin.shopify.com/store/...`). If `host` is missing or wrong, it might use the iframe’s origin (`tryon.global`) by mistake when posting to the parent.
  - **App / URL config**  
    Misconfigured app URL or embed setup in Partners can lead to wrong origin being used.

## What we changed in code

- **`host` in the request**  
  We now pass the `host` query param from the request into the page as `<meta name="shopify-host" content="...">` so the document has it even if the CDN script doesn’t read it from the URL.
- **When we start polling**  
  We wait for `window.load` and a short delay (400 ms) before polling for `getSessionToken`, so App Bridge has time to run and attempt the handshake.
- **Longer polling**  
  80 attempts × 250 ms (about 20 s) before we give up and redirect.

These don’t fix the postMessage bug (that’s in Shopify’s script or its config), but they make our side more robust and give the handshake more time.

## What you should do

1. **Confirm `host` is present**  
   In DevTools → Network, open the app and find the request to `tryon.global/app`. Check that the URL includes **`host=...`** in the query string. If it doesn’t, the app might be loaded in a context where Shopify doesn’t send `host`, which can lead to wrong-origin postMessage.

2. **Confirm App URL in Partners**  
   In Partners → your app → Configuration (or App setup):  
   - **App URL** should be exactly **`https://tryon.global/app`** (no trailing slash, correct domain).  
   - **Embedded** should be **true**.  
   Wrong App URL or non-embedded can contribute to wrong-origin behaviour.

3. **Try with `?debug=1`**  
   Open the embed URL in a new tab and add **`&debug=1`** (e.g. `https://tryon.global/app?shop=...&host=...&debug=1`).  
   - Check the on-page message and the `<pre>` log.  
   - If it says **“URL has host param: true”** and you still get the postMessage error and “Session token: timeout”, the problem is almost certainly in App Bridge / admin, not in our use of `host`.

4. **Report to Shopify**  
   If the request has `host`, App URL is correct, and embedded is true, the “target origin tryon.global vs recipient admin.shopify.com” postMessage behaviour is likely a bug or limitation in the CDN App Bridge or admin when used with a custom (Next.js) app.  
   - Describe: embedded app, App Bridge from CDN, `getSessionToken` never ready, and console error: “postMessage … target origin provided ('https://tryon.global') does not match the recipient window's origin ('https://admin.shopify.com')”.  
   - Ask: how should the app be loaded or configured so that App Bridge uses the parent’s origin for postMessage to admin?

5. **Try an official stack**  
   If you need session token to work soon, try the **Shopify CLI app template** (e.g. Remix or React Router) and see if the same store and app get session token and no postMessage error. If it works there, the difference is likely in how the embedded app is loaded or how App Bridge is initialized in our custom setup.

## Summary

- **Session token is not working** because the App Bridge ↔ admin **postMessage handshake fails** due to **wrong target origin** (`tryon.global` instead of `admin.shopify.com`).
- The fix has to be on the side that sends that postMessage (App Bridge / admin) or in the app/embed configuration that influences it.
- We’ve added `shopify-host` meta, delayed polling until after load, and documented the issue; next steps are to verify `host` and App URL, then either get a proper fix from Shopify or validate with an official template.
