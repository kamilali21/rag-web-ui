import { dashboardConfig } from "../dashboard-layout";

test("hides API Keys from navigation and places Profile last", () => {
  const navigation = dashboardConfig.sidebarNav;
  expect(navigation.map(({ title }) => title)).not.toContain("API Keys");
  expect(navigation[navigation.length - 1]).toMatchObject({ title: "Profile", href: "/dashboard/profile" });
});
