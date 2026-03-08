import { LitElement, html, nothing, type TemplateResult } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { cardStyles } from "./styles";
import type { PackageTrackerCardConfig, PackageEntityAttributes } from "./types";
import "./package-tracker-add-card";

const STATUS_ICONS: Record<string, string> = {
  delivered: "mdi:package-variant-closed-check",
  in_transit: "mdi:truck-delivery",
  out_for_delivery: "mdi:truck-fast",
  pre_transit: "mdi:package-variant",
  exception: "mdi:alert-circle",
  expired: "mdi:clock-alert",
  unknown: "mdi:help-circle",
};

const STATUS_COLORS: Record<string, string> = {
  delivered: "var(--pkg-delivered)",
  in_transit: "var(--pkg-in-transit)",
  out_for_delivery: "var(--pkg-out-for-delivery)",
  pre_transit: "var(--pkg-pre-transit)",
  exception: "var(--pkg-exception)",
  expired: "var(--pkg-expired)",
  unknown: "var(--pkg-unknown)",
};

const STATUS_LABELS: Record<string, string> = {
  delivered: "Delivered",
  in_transit: "In Transit",
  out_for_delivery: "Out for Delivery",
  pre_transit: "Pre-Transit",
  exception: "Exception",
  expired: "Expired",
  unknown: "Unknown",
};

interface PackageData {
  entityId: string;
  state: string;
  attributes: PackageEntityAttributes;
}

@customElement("package-tracker-card")
export class PackageTrackerCard extends LitElement {
  @property({ attribute: false }) public hass: any;
  @state() private _config?: PackageTrackerCardConfig;
  @state() private _refreshing = false;

  static styles = cardStyles;

  public setConfig(config: PackageTrackerCardConfig): void {
    this._config = {
      show_delivered: true,
      ...config,
    };
  }

  public getCardSize(): number {
    return 3;
  }

  public static getConfigElement(): HTMLElement {
    return document.createElement("package-tracker-card-editor");
  }

  public static getStubConfig(): PackageTrackerCardConfig {
    return {
      type: "custom:package-tracker-card",
      title: "Package Tracker",
      show_delivered: true,
    };
  }

  protected render(): TemplateResult | typeof nothing {
    if (!this.hass || !this._config) {
      return nothing;
    }

    const packages = this._getPackages();
    const title = this._config.title ?? "Package Tracker";

    return html`
      <ha-card>
        <div class="card-header">
          <span>${title}</span>
          <div class="header-actions">
            <span class="package-count">${packages.length} package${packages.length !== 1 ? "s" : ""}</span>
            <button
              class="refresh-btn ${this._refreshing ? "spinning" : ""}"
              @click="${this._handleRefresh}"
              title="Refresh all packages"
              ?disabled="${this._refreshing}"
            >
              <ha-icon icon="mdi:refresh"></ha-icon>
            </button>
          </div>
        </div>
        ${packages.length === 0
          ? html`<div class="no-packages">No packages being tracked</div>`
          : html`<div class="package-list">${packages.map((pkg) => this._renderPackage(pkg))}</div>`}
      </ha-card>
    `;
  }

  private async _handleRefresh(): Promise<void> {
    if (this._refreshing || !this.hass) return;
    this._refreshing = true;
    try {
      await this.hass.callService("package_tracker", "refresh_packages", {});
    } catch {
      // Silently handle — HA will show its own error toast
    } finally {
      this._refreshing = false;
    }
  }

  private _getPackages(): PackageData[] {
    const entities = Object.keys(this.hass.states).filter((eid) => {
      if (!eid.startsWith("sensor.")) return false;
      const attrs = this.hass.states[eid].attributes;
      return attrs.tracking_number !== undefined && attrs.carrier !== undefined;
    });

    let packages: PackageData[] = entities.map((entityId) => {
      const stateObj = this.hass.states[entityId];
      return {
        entityId,
        state: stateObj.state,
        attributes: stateObj.attributes as PackageEntityAttributes,
      };
    });

    if (!this._config?.show_delivered) {
      packages = packages.filter((pkg) => pkg.state !== "delivered");
    }

    // Sort: active first (out_for_delivery, in_transit, exception), then pre_transit, then delivered
    const priority: Record<string, number> = {
      out_for_delivery: 0,
      exception: 1,
      in_transit: 2,
      pre_transit: 3,
      unknown: 4,
      expired: 5,
      delivered: 6,
    };
    packages.sort((a, b) => {
      const pa = priority[a.state] ?? 4;
      const pb = priority[b.state] ?? 4;
      if (pa !== pb) return pa - pb;

      const etaA = a.attributes.estimated_delivery
        ? new Date(a.attributes.estimated_delivery).getTime()
        : Infinity;
      const etaB = b.attributes.estimated_delivery
        ? new Date(b.attributes.estimated_delivery).getTime()
        : Infinity;
      return etaA - etaB;
    });

    return packages;
  }

  private _renderPackage(pkg: PackageData): TemplateResult {
    const status = pkg.state || "unknown";
    const icon = STATUS_ICONS[status] || STATUS_ICONS.unknown;
    const color = STATUS_COLORS[status] || STATUS_COLORS.unknown;
    const statusLabel = STATUS_LABELS[status] || status;
    const attrs = pkg.attributes;

    let etaStr = "";
    if (attrs.estimated_delivery) {
      try {
        const date = new Date(attrs.estimated_delivery);
        etaStr = date.toLocaleDateString(undefined, {
          month: "short",
          day: "numeric",
        });
      } catch {
        // ignore
      }
    }

    const latestEvent = attrs.events?.[0]?.description || "";

    return html`
      <div class="package-row" style="border-left-color: ${color}">
        <div class="package-row-primary">
          <span class="package-label">${attrs.label || "Package"}</span>
          <span
            class="status-badge"
            style="color: ${color}; background: color-mix(in srgb, ${color} 12%, transparent)"
          >
            <ha-icon icon="${icon}"></ha-icon>
            ${statusLabel}
          </span>
          ${attrs.tracking_url
            ? html`<a
                class="tracking-link"
                href="${attrs.tracking_url}"
                target="_blank"
                rel="noopener noreferrer"
                title="View on carrier website"
                @click="${(e: Event) => e.stopPropagation()}"
              >
                <ha-icon icon="mdi:open-in-new"></ha-icon>
              </a>`
            : nothing}
        </div>
        <div class="package-row-secondary">
          <div class="secondary-left">
            <span class="carrier-badge">${attrs.carrier || ""}</span>
            <span class="tracking-number">${attrs.tracking_number || ""}</span>
          </div>
          ${etaStr
            ? html`<span class="eta">${status === "delivered" ? etaStr : `ETA: ${etaStr}`}</span>`
            : nothing}
        </div>
        ${latestEvent ? html`<div class="package-row-event">${latestEvent}</div>` : nothing}
      </div>
    `;
  }
}

// Register with Home Assistant card picker
(window as any).customCards = (window as any).customCards || [];
(window as any).customCards.push({
  type: "package-tracker-card",
  name: "Package Tracker Card",
  description: "Track your shipping packages from USPS, UPS, and FedEx",
});
