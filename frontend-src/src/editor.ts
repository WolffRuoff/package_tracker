import { LitElement, html, css, type TemplateResult } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import type { PackageTrackerCardConfig } from "./types";

@customElement("package-tracker-card-editor")
export class PackageTrackerCardEditor extends LitElement {
  @property({ attribute: false }) public hass: any;
  @state() private _config?: PackageTrackerCardConfig;

  static styles = css`
    .editor-row {
      display: flex;
      flex-direction: column;
      gap: 16px;
      padding: 16px;
    }
    .row {
      display: flex;
      align-items: center;
      gap: 8px;
    }
    ha-textfield {
      width: 100%;
    }
  `;

  public setConfig(config: PackageTrackerCardConfig): void {
    this._config = config;
  }

  protected render(): TemplateResult {
    if (!this._config) {
      return html``;
    }

    return html`
      <div class="editor-row">
        <ha-textfield
          label="Title"
          .value=${this._config.title || ""}
          @input=${this._titleChanged}
        ></ha-textfield>
        <div class="row">
          <ha-switch
            .checked=${this._config.show_delivered !== false}
            @change=${this._showDeliveredChanged}
          ></ha-switch>
          <span>Show delivered packages</span>
        </div>
      </div>
    `;
  }

  private _titleChanged(ev: Event): void {
    const target = ev.target as HTMLInputElement;
    this._updateConfig({ title: target.value });
  }

  private _showDeliveredChanged(ev: Event): void {
    const target = ev.target as HTMLInputElement;
    this._updateConfig({ show_delivered: target.checked });
  }

  private _updateConfig(update: Partial<PackageTrackerCardConfig>): void {
    if (!this._config) return;
    this._config = { ...this._config, ...update };
    const event = new CustomEvent("config-changed", {
      detail: { config: this._config },
      bubbles: true,
      composed: true,
    });
    this.dispatchEvent(event);
  }
}
