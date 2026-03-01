import { css } from "lit";

export const cardStyles = css`
  :host {
    --pkg-delivered: #4caf50;
    --pkg-in-transit: #2196f3;
    --pkg-out-for-delivery: #ff9800;
    --pkg-pre-transit: #9e9e9e;
    --pkg-exception: #f44336;
    --pkg-unknown: #757575;
    --pkg-expired: #795548;
  }

  ha-card {
    padding: 16px;
  }

  .card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding-bottom: 12px;
    font-size: 1.2em;
    font-weight: 500;
  }

  .package-count {
    font-size: 0.75em;
    color: var(--secondary-text-color);
  }

  .no-packages {
    text-align: center;
    padding: 24px;
    color: var(--secondary-text-color);
  }

  .package-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .package-row {
    display: flex;
    align-items: center;
    padding: 12px;
    border-radius: 8px;
    background: var(--card-background-color, var(--ha-card-background));
    border: 1px solid var(--divider-color);
    gap: 12px;
  }

  .status-icon {
    flex-shrink: 0;
    width: 40px;
    height: 40px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
  }

  .status-icon ha-icon {
    --mdc-icon-size: 22px;
  }

  .package-info {
    flex: 1;
    min-width: 0;
  }

  .package-label {
    font-weight: 500;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .package-details {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 0.85em;
    color: var(--secondary-text-color);
    margin-top: 2px;
  }

  .carrier-badge {
    display: inline-block;
    padding: 1px 6px;
    border-radius: 4px;
    font-size: 0.75em;
    font-weight: 600;
    text-transform: uppercase;
    background: var(--primary-color);
    color: var(--text-primary-color);
  }

  .tracking-number {
    font-family: monospace;
    font-size: 0.85em;
  }

  .package-status {
    text-align: right;
    flex-shrink: 0;
  }

  .status-text {
    font-size: 0.85em;
    font-weight: 500;
    text-transform: capitalize;
  }

  .eta {
    font-size: 0.75em;
    color: var(--secondary-text-color);
    margin-top: 2px;
  }

  .tracking-link {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    border-radius: 50%;
    color: var(--secondary-text-color);
    text-decoration: none;
    transition: background-color 0.2s, color 0.2s;
  }

  .tracking-link:hover {
    background-color: var(--divider-color);
    color: var(--primary-text-color);
  }

  .tracking-link ha-icon {
    --mdc-icon-size: 18px;
  }
`;
