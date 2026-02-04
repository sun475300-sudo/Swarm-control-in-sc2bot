import { useEffect, useState } from 'react';
import { X, ChevronDown, ChevronRight, Plus, Minus, FileText } from 'lucide-react';
import { getCommitDetails } from '@/lib/github';

interface CommitModalProps {
  owner: string;
  repo: string;
  sha: string;
  onClose: () => void;
}

interface FileChange {
  filename: string;
  status: 'added' | 'removed' | 'modified' | 'renamed';
  additions: number;
  deletions: number;
  changes: number;
  patch?: string;
}

interface CommitDetails {
  sha: string;
  message: string;
  author: {
    name: string;
    email: string;
    date: string;
    avatar_url?: string;
  };
  stats: {
    total: number;
    additions: number;
    deletions: number;
  };
  files: FileChange[];
}

export default function CommitModal({ owner, repo, sha, onClose }: CommitModalProps) {
  const [loading, setLoading] = useState(true);
  const [commitDetails, setCommitDetails] = useState<CommitDetails | null>(null);
  const [expandedFiles, setExpandedFiles] = useState<Set<string>>(new Set());

  useEffect(() => {
    const fetchCommitDetails = async () => {
      setLoading(true);
      try {
        const details = await getCommitDetails(owner, repo, sha);
        if (details) {
          setCommitDetails({
            sha: details.sha,
            message: details.commit.message,
            author: {
              name: details.commit.author.name,
              email: details.commit.author.email,
              date: details.commit.author.date,
              avatar_url: details.author?.avatar_url,
            },
            stats: details.stats,
            files: details.files.map((file: any) => ({
              filename: file.filename,
              status: file.status,
              additions: file.additions,
              deletions: file.deletions,
              changes: file.changes,
              patch: file.patch,
            })),
          });
        }
      } catch (error) {
        console.error('Failed to fetch commit details:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchCommitDetails();
  }, [owner, repo, sha]);

  const toggleFileExpansion = (filename: string) => {
    setExpandedFiles((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(filename)) {
        newSet.delete(filename);
      } else {
        newSet.add(filename);
      }
      return newSet;
    });
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'added':
        return 'text-green-400';
      case 'removed':
        return 'text-red-400';
      case 'modified':
        return 'text-yellow-400';
      case 'renamed':
        return 'text-blue-400';
      default:
        return 'text-gray-400';
    }
  };

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'added':
        return '추가됨';
      case 'removed':
        return '삭제됨';
      case 'modified':
        return '수정됨';
      case 'renamed':
        return '이름변경';
      default:
        return status;
    }
  };

  const renderDiff = (patch: string) => {
    const lines = patch.split('\n');
    return lines.map((line, index) => {
      let className = 'font-mono text-xs px-4 py-0.5';
      let prefix = '';

      if (line.startsWith('+') && !line.startsWith('+++')) {
        className += ' bg-green-500/10 text-green-400';
        prefix = '+';
      } else if (line.startsWith('-') && !line.startsWith('---')) {
        className += ' bg-red-500/10 text-red-400';
        prefix = '-';
      } else if (line.startsWith('@@')) {
        className += ' bg-cyan-500/10 text-cyan-400';
      } else {
        className += ' text-muted-foreground';
      }

      return (
        <div key={index} className={className}>
          <span className="select-none opacity-50 mr-2">{prefix}</span>
          {line}
        </div>
      );
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/80 backdrop-blur-sm">
      <div
        className="glass w-full max-w-4xl max-h-[90vh] overflow-hidden rounded-t-2xl sm:rounded-2xl border border-white/10 bg-background/95 backdrop-blur-md flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* 헤더 */}
        <div className="flex items-center justify-between border-b border-white/10 p-4">
          <h3 className="font-semibold text-lg truncate flex-1 mr-4">커밋 상세</h3>
          <button
            onClick={onClose}
            className="rounded-lg p-2 hover:bg-white/10 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* 콘텐츠 */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="text-center">
                <div className="mb-4 h-8 w-8 animate-spin rounded-full border-4 border-border border-t-accent mx-auto" />
                <p className="text-muted-foreground">로딩 중...</p>
              </div>
            </div>
          ) : commitDetails ? (
            <>
              {/* 커밋 정보 */}
              <div className="glass rounded-lg border border-white/10 bg-white/5 p-4 backdrop-blur-md">
                <div className="flex items-start gap-3 mb-3">
                  {commitDetails.author.avatar_url && (
                    <img
                      src={commitDetails.author.avatar_url}
                      alt={commitDetails.author.name}
                      className="h-10 w-10 rounded-full"
                    />
                  )}
                  <div className="flex-1 min-w-0">
                    <p className="font-medium">{commitDetails.author.name}</p>
                    <p className="text-xs text-muted-foreground">
                      {commitDetails.author.email}
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">
                      {new Date(commitDetails.author.date).toLocaleString('ko-KR')}
                    </p>
                  </div>
                </div>
                <p className="text-sm whitespace-pre-wrap">{commitDetails.message}</p>
                <p className="mt-2 text-xs font-mono text-cyan-400">
                  {commitDetails.sha.substring(0, 7)}
                </p>
              </div>

              {/* 통계 */}
              <div className="glass rounded-lg border border-white/10 bg-white/5 p-4 backdrop-blur-md">
                <div className="flex items-center gap-4 text-sm">
                  <div className="flex items-center gap-2">
                    <FileText className="h-4 w-4 text-muted-foreground" />
                    <span className="font-semibold">{commitDetails.files.length}</span>
                    <span className="text-muted-foreground">파일</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Plus className="h-4 w-4 text-green-400" />
                    <span className="font-semibold text-green-400">
                      +{commitDetails.stats.additions}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Minus className="h-4 w-4 text-red-400" />
                    <span className="font-semibold text-red-400">
                      -{commitDetails.stats.deletions}
                    </span>
                  </div>
                </div>
              </div>

              {/* 파일 변경사항 */}
              <div className="space-y-2">
                <h4 className="font-semibold">파일 변경사항</h4>
                {commitDetails.files.map((file) => (
                  <div
                    key={file.filename}
                    className="glass rounded-lg border border-white/10 bg-white/5 backdrop-blur-md overflow-hidden"
                  >
                    <button
                      onClick={() => toggleFileExpansion(file.filename)}
                      className="w-full flex items-center justify-between p-3 hover:bg-white/5 transition-colors"
                    >
                      <div className="flex items-center gap-2 flex-1 min-w-0">
                        {expandedFiles.has(file.filename) ? (
                          <ChevronDown className="h-4 w-4 flex-shrink-0" />
                        ) : (
                          <ChevronRight className="h-4 w-4 flex-shrink-0" />
                        )}
                        <span className="text-sm font-mono truncate">{file.filename}</span>
                        <span className={`text-xs ${getStatusColor(file.status)}`}>
                          {getStatusLabel(file.status)}
                        </span>
                      </div>
                      <div className="flex items-center gap-2 text-xs flex-shrink-0 ml-2">
                        <span className="text-green-400">+{file.additions}</span>
                        <span className="text-red-400">-{file.deletions}</span>
                      </div>
                    </button>

                    {expandedFiles.has(file.filename) && file.patch && (
                      <div className="border-t border-white/10 bg-black/20 overflow-x-auto">
                        {renderDiff(file.patch)}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="text-center py-12 text-muted-foreground">
              커밋 정보를 불러올 수 없습니다.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
