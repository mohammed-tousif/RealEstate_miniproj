import { describe, expect, it } from "vitest";
import { toQueryString } from "./api";
import { acresAndGuntas, formatArea, formatDate, formatINR, formatINRShort, parseINR, toSqft } from "./format";

describe("INR formatting", () => {
  it("uses Indian digit grouping", () => {
    expect(formatINR("1840000.00")).toBe("₹18,40,000");
    expect(formatINR(125000000)).toBe("₹12,50,00,000");
  });
  it("uses lakh and crore", () => {
    expect(formatINRShort(1840000)).toBe("₹18.4 lakh");
    expect(formatINRShort("2500000.00")).toBe("₹25 lakh");
    expect(formatINRShort(32500000)).toBe("₹3.25 crore");
    expect(formatINRShort(45000)).toBe("₹45,000");
  });
  it("handles bad input", () => {
    expect(formatINR("abc")).toBe("—");
  });
  it("parses lakh/crore text", () => {
    expect(parseINR("25 lakh")).toBe(2500000);
    expect(parseINR("₹1.2 crore")).toBe(12000000);
    expect(parseINR("18,40,000")).toBe(1840000);
    expect(parseINR("20L")).toBe(2000000);
    expect(parseINR("lots")).toBeNull();
  });
});

describe("area helpers", () => {
  it("converts units with the spec's factors", () => {
    expect(toSqft(1, "acre")).toBe(43560);
    expect(toSqft(1, "gunta")).toBe(1089);
    expect(toSqft(40, "gunta")).toBe(43560);
  });
  it("formats areas and farmland notation", () => {
    expect(formatArea("1200.0000", "sqft")).toBe("1,200 sq ft");
    expect(formatArea("2.5", "acre")).toBe("2.5 acres");
    expect(acresAndGuntas(98010)).toBe("2 acres 10 guntas");
    expect(acresAndGuntas(43560)).toBe("1 acre");
    expect(acresAndGuntas(1089)).toBe("1 gunta");
  });
});

describe("misc", () => {
  it("builds query strings with repeated keys and skips empties", () => {
    expect(toQueryString({ city: "Dharwad", property_type: ["a", "b"], q: "", page: 2, x: undefined })).toBe(
      "?city=Dharwad&property_type=a&property_type=b&page=2",
    );
  });
  it("treats zone-less timestamps as UTC", () => {
    expect(formatDate("2026-07-15T10:00:00")).toBe(formatDate("2026-07-15T10:00:00Z"));
  });
});
