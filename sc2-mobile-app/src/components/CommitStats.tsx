import { useEffect, useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend } from 'recharts';
import { TrendingUp, GitCommit, Calendar } from 'lucide-react';
import { getCommits, getRepositoryConfig } from '@/lib/github';

interface CommitActivity {
  date: string;
  count: number;
  day: string;
}

interface AuthorStats {
  name: string;
  count: number;
  color: string;
}

const COLORS = ['#06b6d4', '#8b5cf6', '#ec4899', '#f59e0b', '#10b981', '#3b82f6'];

export default function CommitStats() {
  const [loading, setLoading] = useState(true);
  const [commitActivity, setCommitActivity] = useState<CommitActivity[]>([]);
  const [authorStats, setAuthorStats] = useState<AuthorStats[]>([]);
  const [totalCommits, setTotalCommits] = useState(0);
  const [repoConfig] = useState(getRepositoryConfig());

  useEffect(() => {
    const fetchCommitStats = async () => {
      setLoading(true);
      try {
        // 최근 100개 커밋 가져오기
        const commits = await getCommits(repoConfig.owner, repoConfig.repo, 100);
        
        if (commits.length === 0) {
          setLoading(false);
          return;
        }

        // 날짜별 커밋 수 계산
        const activityMap = new Map<string, number>();
        const authorMap = new Map<string, number>();

        commits.forEach((commit) => {
          // 날짜별 집계
          const date = new Date(commit.author.date);
          const dateKey = date.toISOString().split('T')[0];
          activityMap.set(dateKey, (activityMap.get(dateKey) || 0) + 1);

          // 작성자별 집계
          const author = commit.author.name;
          authorMap.set(author, (authorMap.get(author) || 0) + 1);
        });

        // 날짜별 데이터 변환 (최근 7일)
        const today = new Date();
        const last7Days: CommitActivity[] = [];
        for (let i = 6; i >= 0; i--) {
          const date = new Date(today);
          date.setDate(date.getDate() - i);
          const dateKey = date.toISOString().split('T')[0];
          const dayNames = ['일', '월', '화', '수', '목', '금', '토'];
          
          last7Days.push({
            date: dateKey,
            count: activityMap.get(dateKey) || 0,
            day: dayNames[date.getDay()],
          });
        }

        setCommitActivity(last7Days);

        // 작성자별 데이터 변환 (상위 6명)
        const sortedAuthors = Array.from(authorMap.entries())
          .sort((a, b) => b[1] - a[1])
          .slice(0, 6)
          .map(([name, count], index) => ({
            name,
            count,
            color: COLORS[index % COLORS.length],
          }));

        setAuthorStats(sortedAuthors);
        setTotalCommits(commits.length);
      } catch (error) {
        console.error('Failed to fetch commit stats:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchCommitStats();
  }, [repoConfig]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <div className="mb-4 h-8 w-8 animate-spin rounded-full border-4 border-border border-t-accent mx-auto" />
          <p className="text-muted-foreground">커밋 통계 로딩 중...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 헤더 */}
      <div>
        <h2 className="text-xl font-bold flex items-center gap-2">
          <TrendingUp className="h-5 w-5 text-cyan-400" />
          커밋 활동 통계
        </h2>
        <p className="mt-1 text-sm text-muted-foreground">
          최근 100개 커밋 분석
        </p>
      </div>

      {/* 총 커밋 수 */}
      <div className="glass rounded-lg border border-white/10 bg-white/5 p-6 backdrop-blur-md">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-muted-foreground">총 커밋 수</p>
            <p className="text-3xl font-bold text-cyan-400">{totalCommits}</p>
          </div>
          <GitCommit className="h-12 w-12 text-cyan-400/30" />
        </div>
      </div>

      {/* 최근 7일 커밋 활동 */}
      <div className="glass rounded-lg border border-white/10 bg-white/5 p-6 backdrop-blur-md">
        <h3 className="mb-4 font-semibold flex items-center gap-2">
          <Calendar className="h-4 w-4 text-cyan-400" />
          최근 7일 커밋 활동
        </h3>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={commitActivity}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
            <XAxis 
              dataKey="day" 
              stroke="rgba(255,255,255,0.5)"
              style={{ fontSize: '12px' }}
            />
            <YAxis 
              stroke="rgba(255,255,255,0.5)"
              style={{ fontSize: '12px' }}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: 'rgba(0,0,0,0.8)',
                border: '1px solid rgba(255,255,255,0.1)',
                borderRadius: '8px',
                fontSize: '12px',
              }}
              labelStyle={{ color: '#06b6d4' }}
            />
            <Bar dataKey="count" fill="#06b6d4" radius={[8, 8, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* 작성자별 커밋 수 */}
      {authorStats.length > 0 && (
        <div className="glass rounded-lg border border-white/10 bg-white/5 p-6 backdrop-blur-md">
          <h3 className="mb-4 font-semibold">작성자별 커밋 수</h3>
          <div className="flex flex-col md:flex-row items-center gap-6">
            <div className="w-full md:w-1/2">
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie
                    data={authorStats}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, percent }) => `${name} (${(percent * 100).toFixed(0)}%)`}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="count"
                  >
                    {authorStats.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'rgba(0,0,0,0.8)',
                      border: '1px solid rgba(255,255,255,0.1)',
                      borderRadius: '8px',
                      fontSize: '12px',
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="w-full md:w-1/2 space-y-2">
              {authorStats.map((author) => (
                <div
                  key={author.name}
                  className="flex items-center justify-between p-2 rounded-lg bg-white/5"
                >
                  <div className="flex items-center gap-2">
                    <div
                      className="h-3 w-3 rounded-full"
                      style={{ backgroundColor: author.color }}
                    />
                    <span className="text-sm font-medium truncate">{author.name}</span>
                  </div>
                  <span className="text-sm font-bold text-cyan-400">{author.count}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* 커밋 메시지 키워드 (추가 기능) */}
      <div className="glass rounded-lg border border-white/10 bg-white/5 p-6 backdrop-blur-md">
        <h3 className="mb-3 font-semibold">💡 Tip</h3>
        <p className="text-sm text-muted-foreground">
          더 많은 통계를 보려면 GitHub Insights 페이지를 방문하세요.
        </p>
        <a
          href={`https://github.com/${repoConfig.owner}/${repoConfig.repo}/graphs/contributors`}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-2 inline-block text-sm text-cyan-400 hover:underline"
        >
          GitHub Insights 보기 →
        </a>
      </div>
    </div>
  );
}
