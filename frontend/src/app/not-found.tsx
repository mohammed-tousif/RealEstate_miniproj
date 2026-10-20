import { EmptyState, LinkButton } from "@/components/ui";

export default function NotFound() {
  return (
    <div className="mx-auto max-w-lg px-4 py-20">
      <EmptyState title="Page not found" action={<LinkButton href="/">Go home</LinkButton>} />
    </div>
  );
}
