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

  .header-actions {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .package-count {
    font-size: 0.75em;
    color: var(--secondary-text-color);
  }

  .refresh-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    border-radius: 50%;
    border: none;
    background: none;
    cursor: pointer;
    color: var(--secondary-text-color);
    transition: background-color 0.2s, color 0.2s;
    padding: 0;
  }

  .refresh-btn:hover {
    background-color: var(--divider-color);
    color: var(--primary-text-color);
  }

  .refresh-btn ha-icon {
    --mdc-icon-size: 20px;
  }

  .refresh-btn.spinning ha-icon {
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    from {
      transform: rotate(0deg);
    }
    to {
      transform: rotate(360deg);
    }
  }

  .no-packages {
    text-align: center;
    padding: 24px;
    color: var(--secondary-text-color);
  }

  .package-list {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .package-row {
    display: flex;
    flex-direction: column;
    padding: 16px;
    border-radius: 12px;
    background: var(--card-background-color, var(--ha-card-background));
    border: 1px solid var(--divider-color);
    border-left: 4px solid var(--pkg-unknown);
    gap: 6px;
  }

  .package-row-primary {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .package-label {
    flex: 1;
    font-weight: 500;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    min-width: 0;
  }

  .status-badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 0.75em;
    font-weight: 600;
    white-space: nowrap;
    flex-shrink: 0;
  }

  .status-badge ha-icon {
    --mdc-icon-size: 14px;
  }

  .tracking-link {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 28px;
    height: 28px;
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
    --mdc-icon-size: 16px;
  }

  .package-row-secondary {
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-size: 0.85em;
    color: var(--secondary-text-color);
    gap: 8px;
  }

  .secondary-left {
    display: flex;
    align-items: center;
    gap: 6px;
    min-width: 0;
    overflow: hidden;
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
    flex-shrink: 0;
  }

  .tracking-number {
    font-family: monospace;
    font-size: 0.85em;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .eta {
    font-size: 0.85em;
    color: var(--secondary-text-color);
    white-space: nowrap;
    flex-shrink: 0;
  }

  .package-row-event {
    font-size: 0.8em;
    font-style: italic;
    color: var(--secondary-text-color);
    opacity: 0.8;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
`;
