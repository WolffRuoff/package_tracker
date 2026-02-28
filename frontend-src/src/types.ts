export interface PackageTrackerCardConfig {
  type: string;
  title?: string;
  show_delivered?: boolean;
}

export interface PackageEntityAttributes {
  label: string;
  carrier: string;
  tracking_number: string;
  estimated_delivery: string | null;
  last_updated: string | null;
  raw_status: string;
  events: TrackingEventData[];
}

export interface TrackingEventData {
  timestamp: string;
  location: string;
  description: string;
  status: string;
}
