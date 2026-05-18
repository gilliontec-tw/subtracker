import { describe, it, expect } from "vitest";
import { cn } from "./utils";

describe("cn utility", () => {
  it("joins class names", () => {
    expect(cn("a", "b")).toBe("a b");
    expect(cn("a", "", "b")).toBe("a b");
  });
});
