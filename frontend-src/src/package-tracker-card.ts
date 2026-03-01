import { LitElement, html, nothing, type TemplateResult } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { cardStyles } from "./styles";
import type { PackageTrackerCardConfig, PackageEntityAttributes } from "./types";

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
          <span class="package-count">${packages.length} package${packages.length !== 1 ? "s" : ""}</span>
        </div>
        ${packages.length === 0
          ? html`<div class="no-packages">No packages being tracked</div>`
          : html`<div class="package-list">${packages.map((pkg) => this._renderPackage(pkg))}</div>`}
      </ha-card>
    `;
  }

  private _getPackages(): PackageData[] {
    const entities = Object.keys(this.hass.states).filter((eid) =>
      eid.startsWith("sensor.package_tracker_")
    );

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
    packages.sort(
      (a, b) => (priority[a.state] ?? 4) - (priority[b.state] ?? 4)
    );

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

    return html`
      <div class="package-row">
        <div class="status-icon" style="background-color: ${color}">
          <ha-icon icon="${icon}"></ha-icon>
        </div>
        <div class="package-info">
          <div class="package-label">${attrs.label || "Package"}</div>
          <div class="package-details">
            <span class="carrier-badge">${attrs.carrier || ""}</span>
            <span class="tracking-number">${attrs.tracking_number || ""}</span>
          </div>
        </div>
        <div class="package-status">
          <div class="status-text" style="color: ${color}">${statusLabel}</div>
          ${etaStr ? html`<div class="eta">ETA: ${etaStr}</div>` : nothing}
        </div>
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
