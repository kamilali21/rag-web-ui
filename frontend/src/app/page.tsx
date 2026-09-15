import { redirect } from "next/navigation";

// Added by ChatGPT: open the usable Library; the existing authenticated shell handles sign-in.
export default function Home() {
  redirect("/dashboard/knowledge");
}
