# Official Meta WhatsApp Cloud API setup

This adapter uses direct HTTPS calls to `https://graph.facebook.com/{version}/{phone_number_id}/messages`; it does not use unofficial WhatsApp Web automation.

## Account prerequisites

1. Use your legitimate developer profile and the appropriate business portfolio. Client business assets should remain under the client's control, with authorized technical access for the service provider.
2. Create/configure a Meta application with the WhatsApp product/use case using the dashboard instructions currently available to your account.
3. Start with Meta's test phone number and explicitly permitted recipient numbers. Production requires an eligible business phone, applicable account setup and permissions. Business verification/access requirements depend on the account and operating model.
4. Obtain an access token with messaging permissions for the intended WhatsApp assets. For operations beyond sending, follow current `whatsapp_business_management` and related dashboard requirements. Short-lived test tokens expire; provision an appropriately scoped production token through Meta-supported mechanisms.

## Environment

`META_PHONE_NUMBER_ID` is an asset ID, not the phone's displayed digits. `META_WABA_ID` filters the business account. `META_VERIFY_TOKEN` is your generated handshake secret. `META_APP_SECRET` is the app's secret used for incoming signature validation. `META_ACCESS_TOKEN` authorizes outbound API calls. These values are not interchangeable.

Choose `META_GRAPH_API_VERSION` explicitly from the currently supported versions in the Meta developer dashboard. Automated retrieval of the version documentation was rate-limited during this build, so the project intentionally has no production version default. The mocked `v99.0` used by tests is not a real API version.

## Start and expose the webhook

```bash
python -m src.data.importer
python -m uvicorn src.api:app --host 127.0.0.1 --port 8000
python -m src.worker
```

Expose only the API through a trusted HTTPS reverse proxy/tunnel under your control. Do not expose the local identity-selector UI. Enter `https://YOUR-HOST/webhook` and your verify token in Meta's callback settings, then subscribe to the WhatsApp messages field. Ensure the app is subscribed to the intended WhatsApp Business Account according to current dashboard/API instructions.

The GET handler returns `hub.challenge` only for the expected token and subscribe mode. The POST handler requires the HMAC-SHA256 signature of the exact raw body. Missing secrets fail closed. Delivery/read statuses are acknowledged but do not create inbound conversations.

## Dry run then live

1. Keep `META_DRY_RUN=true`. A valid incoming event is enqueued; the worker records a simulated outbound result without opening an HTTP connection to Meta.
2. Inspect queue status locally. Ensure the LLM is configured and the incoming phone ID matches.
3. For an intentional live inbound reply, set `META_DRY_RUN=false`, configure token/version/phone ID and restart the worker. Send a message from an authorized test recipient to the configured WhatsApp number. Replies must be inside the allowed service window.
4. Outside the service window, the worker blocks free text. Template sending is a separate explicit operation requiring a real approved template name/language and operator confirmation. Local assertions cannot prove Meta approval.

The notebook's optional live Meta block sends one operator-selected approved template after typing `SEND`. It validates outbound acceptance only. It does not prove webhook delivery, message receipt/read, account verification or production readiness.

## Failure states

- Signature rejected: check app secret and preservation of raw request bytes.
- Accepted=0: repeated message ID, status-only event or mismatching phone/WABA.
- Pending: worker stopped or previous job in that conversation unresolved.
- Failed: configuration/client error or exhausted bounded retries. Review before unblocking.
- Uncertain: send timeout/crash/server ambiguity. Reconcile manually before any re-send.
- Blocked: free-text window closed, no automated approved template route.
- Meta account/region/permission error: use Meta support/dashboard; code cannot bypass account restrictions.

## References

- https://developers.facebook.com/documentation/business-messaging/whatsapp/overview
- https://developers.facebook.com/documentation/business-messaging/whatsapp/webhooks/overview
- https://developers.facebook.com/docs/graph-api/changelog/versions/
- https://www.postman.com/meta/whatsapp-business-platform/overview
- https://developers.openai.com/api/docs/guides/function-calling

Meta documentation access was partially rate-limited. Configuration and live tests remain explicit deployment tasks rather than claimed completed checks.
