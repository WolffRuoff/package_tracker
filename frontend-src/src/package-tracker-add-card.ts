import { LitElement, html, nothing, css, type TemplateResult } from "lit";
import { customElement, property, state } from "lit/decorators.js";

@customElement("package-tracker-add-card")
export class PackageTrackerAddCard extends LitElement {
  @property({ attribute: false }) public hass: any;
  @state() private _config?: { type: string; title?: string };

  @state() private _label = "";
  @state() private _trackingNumber = "";
  @state() private _carrier = "";
  @state() private _loading = false;
  @state() private _error = "";
  @state() private _success = false;
  @state() private _carriers: Array<{id: string; name: string}> | null = null;
  private _carriersLoaded = false;

  static styles = css`
    ha-card {
      padding: 16px;
    }

    .card-header {
      font-size: 1.2em;
      font-weight: 500;
      padding-bottom: 16px;
    }

    .form {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    label {
      font-size: 0.85em;
      color: var(--secondary-text-color);
      margin-bottom: 2px;
      display: block;
    }

    input,
    select {
      width: 100%;
      padding: 8px 10px;
      border: 1px solid var(--divider-color);
      border-radius: 6px;
      background: var(--card-background-color, var(--ha-card-background));
      color: var(--primary-text-color);
      font-size: 1em;
      box-sizing: border-box;
    }

    input:focus,
    select:focus {
      outline: none;
      border-color: var(--primary-color);
    }

    button {
      margin-top: 4px;
      padding: 10px;
      background: var(--primary-color);
      color: var(--text-primary-color);
      border: none;
      border-radius: 6px;
      font-size: 1em;
      cursor: pointer;
      transition: opacity 0.2s;
    }

    button:disabled {
      opacity: 0.6;
      cursor: default;
    }

    .message {
      padding: 8px 12px;
      border-radius: 6px;
      font-size: 0.9em;
    }

    .message.error {
      background: rgba(244, 67, 54, 0.1);
      color: var(--error-color, #f44336);
    }

    .message.success {
      background: rgba(76, 175, 80, 0.1);
      color: #4caf50;
    }

    .loading-bar {
      height: 3px;
      width: 100%;
      border-radius: 2px;
      overflow: hidden;
      background: rgba(var(--rgb-primary-color, 33, 150, 243), 0.2);
    }

    .loading-bar-inner {
      height: 100%;
      width: 40%;
      border-radius: 2px;
      background: var(--primary-color);
      animation: loading-pulse 1.2s ease-in-out infinite;
    }

    @keyframes loading-pulse {
      0%   { transform: translateX(-100%); }
      100% { transform: translateX(350%); }
    }
  `;

  public setConfig(config: { type: string; title?: string }): void {
    this._config = config;
  }

  public getCardSize(): number {
    return 3;
  }

  public static getStubConfig(): object {
    return { type: "custom:package-tracker-add-card", title: "Add Package" };
  }

  public static getConfigElement(): HTMLElement {
    return document.createElement("package-tracker-add-card-editor");
  }

  updated(changedProps: Map<string, unknown>) {
    if (changedProps.has("hass") && this.hass && !this._carriersLoaded) {
      this._carriersLoaded = true;
      (this.hass as any)
        .callService("package_tracker", "get_carriers", {}, undefined, false, true)
        .then((result: any) => { this._carriers = result.response?.carriers ?? []; })
        .catch(() => { this._carriers = []; });
    }
  }

  protected render(): TemplateResult | typeof nothing {
    if (!this.hass || !this._config) return nothing;

    return html`
      <ha-card>
        <div class="card-header">${this._config.title ?? "Add Package"}</div>
        <div class="form">
          ${this._error
            ? html`<div class="message error">${this._error}</div>`
            : nothing}
          ${this._success
            ? html`<div class="message success">Package added successfully!</div>`
            : nothing}

          ${this._loading
            ? html`<div class="loading-bar"><div class="loading-bar-inner"></div></div>`
            : nothing}

          <div>
            <label>Label</label>
            <input
              type="text"
              .value="${this._label}"
              placeholder="e.g. Amazon Order"
              @input="${(e: InputEvent) =>
                (this._label = (e.target as HTMLInputElement).value)}"
              @keydown="${(e: KeyboardEvent) => e.key === 'Enter' && this._submit()}"
            />
          </div>

          <div>
            <label>Tracking Number</label>
            <input
              type="text"
              .value="${this._trackingNumber}"
              placeholder="Carrier auto-detected"
              @input="${(e: InputEvent) =>
                (this._trackingNumber = (e.target as HTMLInputElement).value)}"
              @keydown="${(e: KeyboardEvent) => e.key === 'Enter' && this._submit()}"
            />
          </div>

          <div>
            <label>Carrier (optional)</label>
            <select
              ?disabled="${this._carriers === null}"
              .value="${this._carrier}"
              @change="${(e: Event) =>
                (this._carrier = (e.target as HTMLSelectElement).value)}"
            >
              <option value="">Auto-detect</option>
              ${(this._carriers ?? []).map(c => html`<option value="${c.id}">${c.name}</option>`)}
            </select>
          </div>

          <button @click="${this._submit}" ?disabled="${this._loading}">
            ${this._loading ? "Adding…" : "Add Package"}
          </button>
        </div>
      </ha-card>
    `;
  }

  private async _submit(): Promise<void> {
    this._error = "";
    this._success = false;

    if (!this._label.trim() || !this._trackingNumber.trim()) {
      this._error = "Label and tracking number are required.";
      return;
    }

    this._loading = true;
    try {
      await this.hass.callService("package_tracker", "add_package", {
        label: this._label.trim(),
        tracking_number: this._trackingNumber.trim(),
        ...(this._carrier ? { carrier: this._carrier } : {}),
      });
      this._success = true;
      setTimeout(() => { this._success = false; }, 3000);
      this._label = "";
      this._trackingNumber = "";
      this._carrier = "";
    } catch (err: any) {
      this._error = err?.message ?? "Failed to add package. Check your tracking number.";
    } finally {
      this._loading = false;
    }
  }
}

@customElement("package-tracker-add-card-editor")
class PackageTrackerAddCardEditor extends LitElement {
  @property({ attribute: false }) public hass: any;
  @state() private _config?: { type: string; title?: string };

  public setConfig(config: { type: string; title?: string }): void {
    this._config = config;
  }

  protected render() {
    if (!this._config) return nothing;
    return html`
      <div style="padding:16px">
        <ha-textfield
          label="Title"
          .value=${this._config.title ?? "Add Package"}
          @input=${this._titleChanged}
          style="width:100%"
        ></ha-textfield>
      </div>
    `;
  }

  private _titleChanged(ev: Event): void {
    if (!this._config) return;
    this.dispatchEvent(new CustomEvent("config-changed", {
      detail: { config: { ...this._config, title: (ev.target as HTMLInputElement).value } },
      bubbles: true,
      composed: true,
    }));
  }
}

(window as any).customCards = (window as any).customCards || [];
(window as any).customCards.push({
  type: "package-tracker-add-card",
  name: "Package Tracker — Add Package",
  description: "Form card to add a new package to track",
});
