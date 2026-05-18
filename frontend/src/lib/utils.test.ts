import { describe, it, expect } from "vitest";
import { cn } from "./utils";

describe("cn utility", () => {
  it("joins class names", () => {
    expect(cn("a", "b")).toBe("a b");
    expect(cn("a", "", "b")).toBe("a b");
  });

  it("merges conflicting Tailwind classes (last wins)", () => {
    expect(cn("p-4", "p-2")).toBe("p-2");
    expect(cn("text-red-500", "text-blue-500")).toBe("text-blue-500");
  });

  it("handles falsy values", () => {
    expect(cn("a", false, undefined, null, "b")).toBe("a b");
  });
});
