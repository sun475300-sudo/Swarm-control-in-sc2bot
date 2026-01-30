import { useState, useEffect } from 'react';
import { Save, RotateCcw, Key, CheckCircle, XCircle, Bell } from 'lucide-react';
import { getBotConfigs, BotConfig } from '@/lib/api';
import { setGitHubToken, hasGitHubToken, getRateLimit } from '@/lib/github';
import { 
  requestNotificationPermission, 
  getNotificationPermission,
  isPushNotificationSupported 
} from '@/lib/notifications';
import PWAInstallGuide from '@/components/PWAInstallGuide';

export default function Settings() {
  const [botConfigs, setBotConfigs] = useState<BotConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [saved, setSaved] = useState(false);
  const [githubToken, setGithubToken] = useState('');
  const [tokenValid, setTokenValid] = useState<boolean | null>(null);
  const [rateLimit, setRateLimit] = useState<any>(null);
  const [notificationPermission, setNotificationPermission] = useState<NotificationPermission>(
    getNotificationPermission()
  );

  // 설정 상태
  const [settings, setSettings] = useState({
    dashboardUrl: localStorage.getItem('dashboardUrl') || 'https://sc2aidash-bncleqgg.manus.space',
    autoRefreshInterval: parseInt(localStorage.getItem('autoRefreshInterval') || '30'),
    enableNotifications: localStorage.getItem('enableNotifications') !== 'false',
    notifyOnGameEnd: localStorage.getItem('notifyOnGameEnd') !== 'false',
    notifyOnTrainingComplete: localStorage.getItem('notifyOnTrainingComplete') !== 'false',
    notifyOnArenaWin: localStorage.getItem('notifyOnArenaWin') !== 'false',
    darkMode: localStorage.getItem('darkMode') !== 'false',
    soundEnabled: localStorage.getItem('soundEnabled') !== 'false',
  });

  useEffect(() => {
    const fetchConfigs = async () => {
      setLoading(true);
      const configs = await getBotConfigs();
      setBotConfigs(configs);
      setLoading(false);
    };

    fetchConfigs();
    
    // GitHub 토큰 확인
    if (hasGitHubToken()) {
      checkGitHubToken();
    }
    
    // 알림 권한 확인
    setNotificationPermission(getNotificationPermission());
  }, []);
  
  const checkGitHubToken = async () => {
    try {
      const limit = await getRateLimit();
      if (limit) {
        setTokenValid(true);
        setRateLimit(limit);
      } else {
        setTokenValid(false);
      }
    } catch (error) {
      setTokenValid(false);
    }
  };
  
  const handleSaveGitHubToken = () => {
    setGitHubToken(githubToken);
    checkGitHubToken();
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };
  
  const handleRemoveGitHubToken = () => {
    setGitHubToken('');
    setGithubToken('');
    setTokenValid(null);
    setRateLimit(null);
  };
  
  const handleRequestNotificationPermission = async () => {
    const permission = await requestNotificationPermission();
    setNotificationPermission(permission);
    if (permission === 'granted') {
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    }
  };

  const handleSettingChange = (key: string, value: any) => {
    setSettings((prev) => ({ ...prev, [key]: value }));
    setSaved(false);
  };

  const handleSave = () => {
    Object.entries(settings).forEach(([key, value]) => {
      if (typeof value === 'boolean') {
        localStorage.setItem(key, value.toString());
      } else {
        localStorage.setItem(key, String(value));
      }
    });
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };

  const handleReset = () => {
    const defaults = {
      dashboardUrl: 'https://sc2aidash-bncleqgg.manus.space',
      autoRefreshInterval: 30,
      enableNotifications: true,
      notifyOnGameEnd: true,
      notifyOnTrainingComplete: true,
      notifyOnArenaWin: true,
      darkMode: true,
      soundEnabled: true,
    };
    setSettings(defaults);
    setSaved(false);
  };

  return (
    <div className="space-y-6 pb-8">
      {/* GitHub 토큰 설정 */}
      <div className="glass rounded-lg border border-white/10 bg-white/5 p-6 backdrop-blur-md">
        <h3 className="mb-4 font-semibold flex items-center gap-2">
          <Key className="h-5 w-5" />
          GitHub 개인 액세스 토큰
        </h3>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium">Personal Access Token</label>
            <input
              type="password"
              value={githubToken}
              onChange={(e) => setGithubToken(e.target.value)}
              className="mt-2 w-full rounded-lg border border-border bg-white/5 px-4 py-2 text-sm text-foreground placeholder-muted-foreground focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
              placeholder="ghp_xxxxxxxxxxxxxxxxxxxx"
            />
            <p className="mt-1 text-xs text-muted-foreground">
              GitHub API Rate Limit를 향상시키려면 개인 액세스 토큰을 입력하세요.
              <br />
              <a href="https://github.com/settings/tokens/new" target="_blank" rel="noopener noreferrer" className="text-accent hover:underline">
                토큰 생성하기 →
              </a>
            </p>
          </div>
          
          {tokenValid !== null && (
            <div className={`flex items-center gap-2 text-sm ${tokenValid ? 'text-green-400' : 'text-red-400'}`}>
              {tokenValid ? (
                <>
                  <CheckCircle className="h-4 w-4" />
                  <span>토큰이 유효합니다</span>
                </>
              ) : (
                <>
                  <XCircle className="h-4 w-4" />
                  <span>토큰이 유효하지 않습니다</span>
                </>
              )}
            </div>
          )}
          
          {rateLimit && (
            <div className="rounded-lg bg-white/5 p-3 text-xs">
              <p className="font-medium mb-1">API Rate Limit</p>
              <p className="text-muted-foreground">
                사용 가능: {rateLimit.remaining} / {rateLimit.limit}
              </p>
              <p className="text-muted-foreground">
                리셋 시간: {rateLimit.reset.toLocaleTimeString()}
              </p>
            </div>
          )}
          
          <div className="flex gap-2">
            <button
              onClick={handleSaveGitHubToken}
              disabled={!githubToken}
              className="flex-1 rounded-lg bg-accent px-4 py-2 text-sm font-medium text-accent-foreground hover:bg-accent/90 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              토큰 저장
            </button>
            {hasGitHubToken() && (
              <button
                onClick={handleRemoveGitHubToken}
                className="rounded-lg bg-red-500/20 px-4 py-2 text-sm font-medium text-red-400 hover:bg-red-500/30"
              >
                토큰 제거
              </button>
            )}
          </div>
        </div>
      </div>

      {/* 대시보드 연결 */}
      <div className="glass rounded-lg border border-white/10 bg-white/5 p-6 backdrop-blur-md">
        <h3 className="mb-4 font-semibold">대시보드 연결</h3>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium">대시보드 URL</label>
            <input
              type="url"
              value={settings.dashboardUrl}
              onChange={(e) =>
                handleSettingChange('dashboardUrl', e.target.value)
              }
              className="mt-2 w-full rounded-lg border border-border bg-white/5 px-4 py-2 text-sm text-foreground placeholder-muted-foreground focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
              placeholder="https://sc2aidash-bncleqgg.manus.space"
            />
            <p className="mt-1 text-xs text-muted-foreground">
              웹 대시보드의 URL을 입력하세요.
            </p>
          </div>
        </div>
      </div>

      {/* 새로고침 설정 */}
      <div className="glass rounded-lg border border-white/10 bg-white/5 p-6 backdrop-blur-md">
        <h3 className="mb-4 font-semibold">새로고침 설정</h3>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium">
              자동 새로고침 간격 (초)
            </label>
            <input
              type="number"
              min="5"
              max="300"
              step="5"
              value={settings.autoRefreshInterval}
              onChange={(e) =>
                handleSettingChange(
                  'autoRefreshInterval',
                  parseInt(e.target.value)
                )
              }
              className="mt-2 w-full rounded-lg border border-border bg-white/5 px-4 py-2 text-sm text-foreground focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
            />
            <p className="mt-1 text-xs text-muted-foreground">
              {settings.autoRefreshInterval}초마다 데이터를 새로고침합니다.
            </p>
          </div>
        </div>
      </div>

      {/* 알림 설정 */}
      <div className="glass rounded-lg border border-white/10 bg-white/5 p-6 backdrop-blur-md">
        <h3 className="mb-4 font-semibold flex items-center gap-2">
          <Bell className="h-5 w-5" />
          알림 설정
        </h3>
        <div className="space-y-4">
          {/* 알림 권한 상태 */}
          {isPushNotificationSupported() && (
            <div className="rounded-lg bg-white/5 p-4 border border-white/10">
              <div className="flex items-center justify-between mb-3">
                <div>
                  <p className="text-sm font-medium">브라우저 알림 권한</p>
                  <p className="text-xs text-muted-foreground mt-1">
                    {notificationPermission === 'granted' 
                      ? '✅ 알림이 허용되었습니다'
                      : notificationPermission === 'denied'
                      ? '❌ 알림이 차단되었습니다. 브라우저 설정에서 변경하세요.'
                      : '⚠️ 알림 권한이 필요합니다'}
                  </p>
                </div>
                <div className={`h-3 w-3 rounded-full ${
                  notificationPermission === 'granted' 
                    ? 'bg-green-500' 
                    : notificationPermission === 'denied'
                    ? 'bg-red-500'
                    : 'bg-yellow-500'
                }`} />
              </div>
              {notificationPermission !== 'granted' && notificationPermission !== 'denied' && (
                <button
                  onClick={handleRequestNotificationPermission}
                  className="w-full rounded-lg bg-accent px-4 py-2 text-sm font-medium text-accent-foreground hover:bg-accent/90"
                >
                  알림 권한 요청
                </button>
              )}
            </div>
          )}
          
          <label className="flex items-center gap-3">
            <input
              type="checkbox"
              checked={settings.enableNotifications}
              onChange={(e) =>
                handleSettingChange('enableNotifications', e.target.checked)
              }
              className="h-4 w-4 rounded border-border bg-white/5 accent-accent"
            />
            <span className="text-sm font-medium">알림 활성화</span>
          </label>

          {settings.enableNotifications && (
            <div className="space-y-3 border-t border-white/10 pt-4">
              <label className="flex items-center gap-3">
                <input
                  type="checkbox"
                  checked={settings.notifyOnGameEnd}
                  onChange={(e) =>
                    handleSettingChange('notifyOnGameEnd', e.target.checked)
                  }
                  className="h-4 w-4 rounded border-border bg-white/5 accent-accent"
                />
                <span className="text-sm">게임 종료 시 알림</span>
              </label>

              <label className="flex items-center gap-3">
                <input
                  type="checkbox"
                  checked={settings.notifyOnTrainingComplete}
                  onChange={(e) =>
                    handleSettingChange(
                      'notifyOnTrainingComplete',
                      e.target.checked
                    )
                  }
                  className="h-4 w-4 rounded border-border bg-white/5 accent-accent"
                />
                <span className="text-sm">학습 완료 시 알림</span>
              </label>

              <label className="flex items-center gap-3">
                <input
                  type="checkbox"
                  checked={settings.notifyOnArenaWin}
                  onChange={(e) =>
                    handleSettingChange('notifyOnArenaWin', e.target.checked)
                  }
                  className="h-4 w-4 rounded border-border bg-white/5 accent-accent"
                />
                <span className="text-sm">Arena 승리 시 알림</span>
              </label>

              <label className="flex items-center gap-3">
                <input
                  type="checkbox"
                  checked={settings.soundEnabled}
                  onChange={(e) =>
                    handleSettingChange('soundEnabled', e.target.checked)
                  }
                  className="h-4 w-4 rounded border-border bg-white/5 accent-accent"
                />
                <span className="text-sm">알림 소리 활성화</span>
              </label>
            </div>
          )}
        </div>
      </div>

      {/* 테마 설정 */}
      <div className="glass rounded-lg border border-white/10 bg-white/5 p-6 backdrop-blur-md">
        <h3 className="mb-4 font-semibold">테마</h3>
        <div className="space-y-4">
          <label className="flex items-center gap-3">
            <input
              type="checkbox"
              checked={settings.darkMode}
              onChange={(e) =>
                handleSettingChange('darkMode', e.target.checked)
              }
              className="h-4 w-4 rounded border-border bg-white/5 accent-accent"
            />
            <span className="text-sm font-medium">다크 모드</span>
          </label>
        </div>
      </div>

      {/* 봇 설정 정보 */}
      {!loading && botConfigs.length > 0 && (
        <div className="glass rounded-lg border border-white/10 bg-white/5 p-6 backdrop-blur-md">
          <h3 className="mb-4 font-semibold">활성 봇 설정</h3>
          <div className="space-y-3">
            {botConfigs
              .filter((config) => config.isActive)
              .map((config) => (
                <div
                  key={config.id}
                  className="rounded-lg bg-white/5 p-4"
                >
                  <h4 className="font-semibold text-cyan-400">
                    {config.name}
                  </h4>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {config.description}
                  </p>
                  <p className="mt-2 text-xs">
                    <span className="font-medium">전략:</span> {config.strategy}
                  </p>
                </div>
              ))}
          </div>
        </div>
      )}

      {/* PWA 설치 가이드 */}
      <div className="glass rounded-lg border border-white/10 bg-white/5 p-6 backdrop-blur-md">
        <h3 className="mb-4 font-semibold">📱 앱 설치하기</h3>
        <PWAInstallGuide />
      </div>

      {/* 저장 버튼 */}
      <div className="sticky bottom-0 flex gap-3 bg-background/80 backdrop-blur-sm pt-4">
        <button
          onClick={handleSave}
          className="flex-1 inline-flex items-center justify-center gap-2 rounded-lg bg-accent px-4 py-3 font-medium text-accent-foreground hover:bg-accent/90 transition-colors"
        >
          <Save className="h-5 w-5" />
          저장
        </button>
        <button
          onClick={handleReset}
          className="flex-1 inline-flex items-center justify-center gap-2 rounded-lg bg-secondary px-4 py-3 font-medium text-muted-foreground hover:bg-secondary/80 transition-colors"
        >
          <RotateCcw className="h-5 w-5" />
          초기화
        </button>
      </div>

      {/* 저장 완료 메시지 */}
      {saved && (
        <div className="fixed bottom-4 left-4 right-4 rounded-lg bg-green-500/20 border border-green-500/50 px-4 py-3 text-sm font-medium text-green-400">
          설정이 저장되었습니다.
        </div>
      )}
    </div>
  );
}
