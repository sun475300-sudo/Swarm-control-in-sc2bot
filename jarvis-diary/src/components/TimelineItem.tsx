export default function TimelineItem({
    date,
    title,
    description,
    status = "completed",
    isLast = false
}: {
    date: string,
    title: string,
    description: string,
    status?: "completed" | "in-progress" | "planned",
    isLast?: boolean
}) {
    const statusColors = {
        "completed": "bg-accent",
        "in-progress": "bg-primary animate-pulse",
        "planned": "bg-secondary"
    };

    return (
        <div className="flex group">
            <div className="flex flex-col items-center mr-6">
                <div className={`w-4 h-4 rounded-full ${statusColors[status]} ring-4 ring-background z-10`} />
                {!isLast && <div className="w-0.5 h-full bg-border group-hover:bg-primary/50 transition-colors" />}
            </div>
            <div className="pb-12 pt-0.5">
                <span className="text-xs font-bold text-primary uppercase tracking-widest">{date}</span>
                <h3 className="text-xl font-bold mt-1 font-display">{title}</h3>
                <p className="text-muted-foreground mt-2 text-sm leading-relaxed max-w-lg">
                    {description}
                </p>
            </div>
        </div>
    );
}
