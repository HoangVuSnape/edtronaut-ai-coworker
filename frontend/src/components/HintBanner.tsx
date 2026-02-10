// Hint Banner
// ---
// Displays coaching hints from the Director agent when the learner is
// stuck or needs guidance.  Only visible when a non-empty hint exists.

import './HintBanner.css';

interface HintBannerProps {
    hint?: string;
    onDismiss?: () => void;
}

export function HintBanner({ hint, onDismiss }: HintBannerProps) {
    if (!hint) return null;

    return (
        <div className="hint-banner" role="status" aria-live="polite">
            <div className="hint-icon">💡</div>
            <p className="hint-text">{hint}</p>
            {onDismiss && (
                <button className="hint-dismiss" onClick={onDismiss} aria-label="Dismiss hint">
                    ✕
                </button>
            )}
        </div>
    );
}
