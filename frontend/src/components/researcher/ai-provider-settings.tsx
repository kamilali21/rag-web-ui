"use client";

import { useEffect, useState } from "react";
import { KeyRound, Loader2, Save, Trash2 } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";

type Saved = { configured: boolean; provider: "openrouter" | "openai" | null; model: string | null; key_last4: string | null };
const empty: Saved = { configured: false, provider: null, model: null, key_last4: null };
const openaiModels = ["gpt-4.1-mini", "gpt-4.1", "gpt-4o-mini", "gpt-4o"];

export function AIProviderSettings() {
  const [saved, setSaved] = useState<Saved>(empty);
  const [provider, setProvider] = useState<"openrouter" | "openai">("openrouter");
  const [model, setModel] = useState("openrouter/free");
  const [key, setKey] = useState("");
  const [consent, setConsent] = useState(false);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const reflect = (value: Saved) => {
    setSaved(value); setProvider(value.provider || "openrouter"); setModel(value.model || "openrouter/free");
    setKey(""); setConsent(false);
  };
  useEffect(() => {
    const controller = new AbortController();
    void api.get("/api/ai-settings", { signal: controller.signal, cache: "no-store" })
      .then(value => { if (!controller.signal.aborted) reflect(value); })
      .catch(() => { if (!controller.signal.aborted) setError("Could not load AI settings. Refresh to retry."); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, []);
  const act = async (kind: "save" | "check" | "remove") => {
    setBusy(true); setError(""); setNotice("");
    try {
      if (kind === "save") {
        reflect(await api.put("/api/ai-settings", { provider, model, ...(key ? { api_key: key } : {}), consent }));
        setNotice("Private AI settings saved. New AI requests use this provider and model.");
      } else if (kind === "remove") {
        reflect(await api.delete("/api/ai-settings"));
        setNotice("Personal key removed. New AI requests use the application's default provider.");
      } else {
        const result = await api.post("/api/ai-settings/check"); setNotice(result.message);
      }
    } catch (failure) {
      setError(failure instanceof ApiError ? failure.message : "AI settings request failed. Please try again.");
    } finally { setKey(""); setBusy(false); }
  };
  return <section className="researcher-profile-card ai-provider-settings" aria-labelledby="ai-settings-title">
    <header><div className="flex items-center gap-2"><KeyRound size={21} aria-hidden="true" /><h2 id="ai-settings-title">Your AI provider</h2></div>
      <p>Use your own key for Chat, Summarize, Analyse and Compare. Indexing still uses the application’s embedding service.</p></header>
    {loading ? <p role="status">Loading AI settings...</p> : <>
      <p className="researcher-notice">{saved.configured ? `Personal ${saved.provider === "openai" ? "OpenAI" : "OpenRouter"} key ending ${saved.key_last4} · ${saved.model}` : "Using the application's default AI provider."}</p>
      <form onSubmit={event => { event.preventDefault(); void act("save"); }}>
        <fieldset disabled={busy} className="ai-provider-fields">
          <label htmlFor="ai-provider">Provider<select id="ai-provider" className="public-input" value={provider}
            onChange={event => { const value = event.target.value as "openrouter" | "openai"; setProvider(value); setModel(value === "openai" ? "gpt-4.1-mini" : "openrouter/free"); setKey(""); setConsent(false); }}>
            <option value="openrouter">OpenRouter</option><option value="openai">OpenAI</option></select></label>
          <label htmlFor="ai-model">Model{provider === "openai" ?
            <select id="ai-model" className="public-input" value={model} onChange={event => setModel(event.target.value)}>{openaiModels.map(item => <option key={item}>{item}</option>)}</select> :
            <input id="ai-model" className="public-input" required maxLength={160} value={model} onChange={event => setModel(event.target.value)} placeholder="openrouter/free" />}</label>
          <label htmlFor="ai-key" className="researcher-wide">{saved.configured && saved.provider === provider ? "Replace API key (leave blank to keep saved key)" : "API key"}
            <input id="ai-key" className="public-input" type="password" autoComplete="off" spellCheck={false} maxLength={512}
              required={!saved.configured || saved.provider !== provider} value={key} onChange={event => setKey(event.target.value)} aria-describedby="ai-key-privacy" /></label>
          <p id="ai-key-privacy" className="researcher-wide">Keys are encrypted on the server and never displayed again. Other users and admin screens cannot read them. A personal-key failure never switches to the shared key.</p>
          <label className="ai-provider-consent researcher-wide"><input type="checkbox" checked={consent} required onChange={event => setConsent(event.target.checked)} />
            <span>I understand my provider may charge my account and receive the prompts and permitted document passages needed for AI requests. Connection checks make a small AI request.</span></label>
          <div className="ai-provider-actions researcher-wide">
            <Button type="submit" disabled={busy || !consent}>{busy ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />} Save AI settings</Button>
            {saved.configured && <><Button type="button" variant="outline" disabled={busy} onClick={() => void act("check")}>Check saved connection</Button>
              <Button type="button" variant="outline" disabled={busy} onClick={() => void act("remove")}><Trash2 size={16} /> Remove personal key</Button></>}
          </div>
        </fieldset>
      </form>
      <small>OpenRouter models must support JSON and structured outputs. Free models still have limits. OpenAI API billing is separate from a ChatGPT subscription. Choose a provider/model within your budget.</small>
    </>}
    {error && <p role="alert" className="corpus-error">{error}</p>}
    {notice && <p role="status" className="researcher-notice">{notice}</p>}
  </section>;
}
