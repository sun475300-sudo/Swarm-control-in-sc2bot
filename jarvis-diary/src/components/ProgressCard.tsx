export default function ProgressCard({
    title,
    value,
    label,
    icon: Icon
}: {
    title: string,
    value: string | number,
    label: string,
    icon: any
}) {
    return (
        <div className="glass p-6 rounded-3xl glass-hover">
            <div className="flex items-center justify-between mb-4">
                <span className="text-xs font-bold text-muted-foreground uppercase tracking-widest">{title}</span>
                <div className="w-8 h-8 bg-primary/10 text-primary rounded-lg flex items-center justify-center">
                    <Icon className="w-4 h-4" />
                </div>
            </div>
            <div className="text-3xl font-display font-bold mb-1">{value}</div>
            <div className="text-xs text-accent font-medium">{label}</div>
        </div>
    );
}
