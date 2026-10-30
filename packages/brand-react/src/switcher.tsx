'use client';

import { brandCatalog, getPublicBrandSites } from 'meathill-brand';
import {
  type CSSProperties,
  type SyntheticEvent,
  useId,
  useRef,
  useState,
} from 'react';

export interface BrandSiteSwitcherProps {
  currentSiteId: string;
  locale?: string;
}

interface AnchorStyle extends CSSProperties {
  anchorName?: string;
  positionAnchor?: string;
}

interface SwitcherLabels {
  allProducts: string;
  current: string;
  network: string;
}

const POPOVER_GAP = 6;
const VIEWPORT_EDGE_PADDING = 8;

function resolveSwitcherLabels(locale = 'zh'): SwitcherLabels {
  if (locale.toLowerCase().startsWith('zh')) {
    return {
      allProducts: '全部产品',
      current: '当前站点',
      network: '产品网络',
    };
  }
  return {
    allProducts: 'All products',
    current: 'Current site',
    network: 'Product network',
  };
}

export function BrandSiteSwitcher({
  currentSiteId,
  locale,
}: BrandSiteSwitcherProps) {
  const labels = resolveSwitcherLabels(locale);
  const sites = getPublicBrandSites();
  const rawId = useId();
  const safeId = rawId.replace(/[^a-zA-Z0-9_-]/g, '-');
  const popoverId = `meathill-brand-menu-${safeId}`;
  const anchorName = `--meathill-anchor-${safeId}`;
  const triggerRef = useRef<HTMLButtonElement | null>(null);
  const [isOpen, setIsOpen] = useState(false);

  const triggerStyle: AnchorStyle = { anchorName };
  const panelStyle: AnchorStyle = { positionAnchor: anchorName };

  function handleToggle(event: SyntheticEvent<HTMLDivElement>) {
    const panel = event.currentTarget;
    const nextOpen = panel.matches(':popover-open');
    setIsOpen(nextOpen);

    if (
      nextOpen &&
      triggerRef.current &&
      typeof CSS !== 'undefined' &&
      !CSS.supports('position-area: block-end')
    ) {
      const rect = triggerRef.current.getBoundingClientRect();
      const maxLeft = Math.max(
        VIEWPORT_EDGE_PADDING,
        window.innerWidth - panel.offsetWidth - VIEWPORT_EDGE_PADDING,
      );
      const left = Math.min(
        maxLeft,
        Math.max(VIEWPORT_EDGE_PADDING, rect.right - panel.offsetWidth),
      );
      let top = rect.bottom + POPOVER_GAP;
      if (
        top + panel.offsetHeight > window.innerHeight - VIEWPORT_EDGE_PADDING &&
        rect.top - POPOVER_GAP - panel.offsetHeight >= VIEWPORT_EDGE_PADDING
      ) {
        top = rect.top - POPOVER_GAP - panel.offsetHeight;
      }
      panel.style.left = `${Math.round(left)}px`;
      panel.style.top = `${Math.round(Math.max(VIEWPORT_EDGE_PADDING, top))}px`;
    }
  }

  return (
    <div className="meathill-brand-switcher">
      <button
        aria-expanded={isOpen}
        className="meathill-brand-switcher-trigger"
        popoverTarget={popoverId}
        ref={triggerRef}
        style={triggerStyle}
        type="button"
      >
        <span>{labels.network}</span>
        <span aria-hidden="true" className="meathill-brand-switcher-chevron" />
      </button>
      <div
        className="meathill-brand-switcher-panel"
        id={popoverId}
        onToggle={handleToggle}
        popover="auto"
        style={panelStyle}
      >
        <ul>
          {sites.map((site) => (
            <li key={site.id}>
              <a
                aria-current={site.id === currentSiteId ? 'page' : undefined}
                href={site.url}
              >
                <span>{site.name}</span>
                {site.id === currentSiteId ? <small>{labels.current}</small> : null}
              </a>
            </li>
          ))}
        </ul>
        <hr className="meathill-brand-switcher-separator" />
        <a
          className="meathill-brand-directory-link"
          href={brandCatalog.directoryUrl}
        >
          <span>{labels.allProducts}</span>
          <span aria-hidden="true">→</span>
        </a>
      </div>
    </div>
  );
}
