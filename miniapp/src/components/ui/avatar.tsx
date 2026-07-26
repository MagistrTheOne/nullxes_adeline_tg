import { cn } from "@/lib/utils";

type AvatarProps = {
  src?: string;
  alt?: string;
  fallback?: string;
  className?: string;
};

export function Avatar({ src, alt = "", fallback = "AK", className }: AvatarProps) {
  return (
    <div
      className={cn(
        "relative flex h-10 w-10 shrink-0 overflow-hidden rounded-full bg-secondary",
        className,
      )}
    >
      {src ? (
        <img src={src} alt={alt} className="aspect-square h-full w-full object-cover" />
      ) : (
        <span className="flex h-full w-full items-center justify-center text-xs font-semibold text-muted-foreground">
          {fallback}
        </span>
      )}
    </div>
  );
}
