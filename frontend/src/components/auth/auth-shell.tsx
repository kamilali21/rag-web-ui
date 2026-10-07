import type { ReactNode } from "react";
import { ArrowDown, ArrowUpRight, BookOpen, FileText, GitCompareArrows, Quote, Search, Sprout } from "lucide-react";

/** Presentation only: authentication stays in the existing child components. */
export default function AuthShell({ children }: { children: ReactNode }) {
  return (
    <main className="auth-page">
      <header className="auth-masthead">
        <div className="auth-wordmark"><BookOpen aria-hidden="true" size={30} strokeWidth={1.5} />rAGRI search</div>
        <a className="auth-form-shortcut" href="#auth-panel">Get started <ArrowDown aria-hidden="true" size={16} /></a>
      </header>

      <div className="auth-layout">
        <section className="auth-story" aria-labelledby="auth-hero-title">
          <p className="auth-eyebrow"><span aria-hidden="true" />RESEARCH INTELLIGENCE</p>
          <h1 id="auth-hero-title">Research faster.<br /><span>Discover what matters.</span></h1>
          <p className="auth-intro">Explore university research, compare studies, discover candidate research gaps, and get evidence-backed answers with citations. Bring your next insight into focus with rAGRI search.</p>
          <ul className="auth-capabilities" aria-label="Research capabilities">
            <li>Semantic Research Search</li><li>Cited AI Answers</li>
            <li>Compare Studies</li><li>Find Research Gaps</li>
          </ul>

          <figure className="auth-research-visual" aria-label="Illustrative research workspace with connected papers and cited evidence">
            <div className="auth-research-scene" aria-hidden="true">
              <div className="auth-campus">
                <img src="/uafbanner.jpg" alt="" width={468} height={654} />
                <div><span>ROOTED IN RESEARCH</span><strong>Made for<br />new perspectives.</strong><small>University of Agriculture,<br />Faisalabad</small></div>
              </div>
              <div className="auth-semantic-query"><Search size={15} /><span>What connects these studies?</span><ArrowUpRight size={15} /></div>
              <svg className="auth-evidence-connector" viewBox="0 0 560 310" fill="none" preserveAspectRatio="none">
                <path d="M325 43 V65 Q325 76 340 76 H463 Q479 76 479 92 V214 Q479 231 459 231 H352" />
              </svg>
              <div className="auth-paper auth-paper-back">
                <FileText size={17} /><div><strong>Soil health &amp; crop resilience</strong><small>Example author · Soil Science</small></div>
              </div>
              <div className="auth-paper auth-paper-front">
                <div className="auth-paper-heading"><span><FileText size={16} /> RESEARCH PAPER</span><span>01</span></div>
                <strong className="auth-paper-title">Water-smart farming:<br />from evidence to insight</strong>
                <p className="auth-paper-meta">Example author · Agronomy</p>
                <div className="auth-evidence"><Quote size={16} /><p>Comparing field conditions helps explain differences between studies.</p></div>
                <div className="auth-paper-citation"><span>[1] Evidence linked</span><small>Source passage · p. 4</small></div>
              </div>
              <div className="auth-discovery"><span><GitCompareArrows size={15} />Compare methods</span><span><Sprout size={15} />Research gap</span></div>
            </div>
            <figcaption>From research papers to connected evidence <span>Illustrative preview</span></figcaption>
          </figure>
          <p className="auth-institution"><span aria-hidden="true" />Research intelligence built for UAF</p>
        </section>

        <section className="auth-panel" id="auth-panel" aria-label="Account access" tabIndex={-1}>
          <div className="auth-panel-glow" aria-hidden="true" />
          <div className="auth-card">
            <div className="auth-card-kicker"><BookOpen size={18} aria-hidden="true" /><span>YOUR RESEARCH WORKSPACE</span></div>
            <div className="auth-form-content">{children}</div>
          </div>
          <p className="auth-panel-note">A place for your papers.<br /><strong>A clearer path to your next discovery.</strong></p>
        </section>
      </div>
      <footer className="auth-footer"><span>rAGRI search</span><span>Read deeply. Think across studies.</span></footer>
    </main>
  );
}
