export function mw(value: number | null | undefined, digits = 0): string {
  if (value == null || Number.isNaN(value)) return "–";
  return value.toLocaleString("en-GB", {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
  });
}

export function signedMw(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "–";
  const formatted = mw(Math.abs(value), 0);
  if (value > 0) return `+${formatted}`;
  if (value < 0) return `−${formatted}`;
  return formatted;
}

export function utcLabel(iso: string, withDate = true): string {
  const stamp = new Date(iso);
  return new Intl.DateTimeFormat("en-GB", {
    day: withDate ? "2-digit" : undefined,
    month: withDate ? "short" : undefined,
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
    timeZone: "UTC",
  }).format(stamp);
}

export function hourLabel(hour: number): string {
  return `${hour.toString().padStart(2, "0")}:00`;
}

export function dayLabel(isoDate: string): string {
  const [year, month, day] = isoDate.slice(0, 10).split("-").map(Number);
  const stamp = new Date(Date.UTC(year, month - 1, day));
  return new Intl.DateTimeFormat("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  }).format(stamp);
}

export function dayTick(iso: string): string {
  const stamp = new Date(iso);
  return new Intl.DateTimeFormat("en-GB", {
    day: "numeric",
    month: "short",
    timeZone: "UTC",
  }).format(stamp);
}

export function cutoffLabel(iso: string): string {
  const stamp = new Date(iso);
  const day = new Intl.DateTimeFormat("en-GB", {
    day: "numeric",
    month: "short",
    timeZone: "UTC",
  }).format(stamp);
  const clock = new Intl.DateTimeFormat("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
    timeZone: "UTC",
  }).format(stamp);
  return `${day} ${clock} UTC`;
}
