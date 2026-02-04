import { useState } from 'react';
import { Download, Smartphone, Monitor, HelpCircle, CheckCircle, XCircle } from 'lucide-react';

export default function PWAInstallGuide() {
  const [isStandalone, setIsStandalone] = useState(
    window.matchMedia('(display-mode: standalone)').matches ||
    ('standalone' in window.navigator && (window.navigator as any).standalone)
  );

  const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent);
  const isAndroid = /Android/.test(navigator.userAgent);
  const isMobile = isIOS || isAndroid;

  return (
    <div className="space-y-4">
      {/* 설치 상태 */}
      <div className={`glass rounded-lg border p-4 backdrop-blur-md ${
        isStandalone 
          ? 'border-green-500/30 bg-green-500/10' 
          : 'border-yellow-500/30 bg-yellow-500/10'
      }`}>
        <div className="flex items-center gap-3">
          {isStandalone ? (
            <CheckCircle className="h-6 w-6 text-green-400" />
          ) : (
            <Download className="h-6 w-6 text-yellow-400" />
          )}
          <div>
            <p className="font-semibold">
              {isStandalone ? '✅ 앱이 설치되었습니다!' : '📱 앱 설치 가능'}
            </p>
            <p className="text-sm text-muted-foreground">
              {isStandalone 
                ? '홈 화면에서 앱을 실행 중입니다.' 
                : '홈 화면에 추가하여 더 빠르게 사용하세요.'}
            </p>
          </div>
        </div>
      </div>

      {!isStandalone && (
        <>
          {/* iOS 설치 안내 */}
          {isIOS && (
            <div className="glass rounded-lg border border-white/10 bg-white/5 p-4 backdrop-blur-md">
              <div className="flex items-start gap-3">
                <Smartphone className="h-6 w-6 text-cyan-400 flex-shrink-0" />
                <div className="flex-1">
                  <h3 className="font-semibold mb-2">iPhone/iPad 설치 방법</h3>
                  <ol className="space-y-2 text-sm text-muted-foreground">
                    <li className="flex gap-2">
                      <span className="font-bold text-cyan-400">1.</span>
                      <span>Safari 브라우저로 이 페이지를 여세요</span>
                    </li>
                    <li className="flex gap-2">
                      <span className="font-bold text-cyan-400">2.</span>
                      <span>하단 중앙의 <strong>공유 버튼 (□↑)</strong> 을 탭하세요</span>
                    </li>
                    <li className="flex gap-2">
                      <span className="font-bold text-cyan-400">3.</span>
                      <span>아래로 스크롤하여 <strong>"홈 화면에 추가"</strong> 를 선택하세요</span>
                    </li>
                    <li className="flex gap-2">
                      <span className="font-bold text-cyan-400">4.</span>
                      <span><strong>"추가"</strong> 버튼을 탭하세요</span>
                    </li>
                  </ol>
                  <div className="mt-3 p-2 rounded bg-yellow-500/10 border border-yellow-500/30">
                    <p className="text-xs text-yellow-400">
                      ⚠️ <strong>중요:</strong> Safari 브라우저에서만 설치 가능합니다. Chrome, Firefox는 지원하지 않습니다.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Android 설치 안내 */}
          {isAndroid && (
            <div className="glass rounded-lg border border-white/10 bg-white/5 p-4 backdrop-blur-md">
              <div className="flex items-start gap-3">
                <Smartphone className="h-6 w-6 text-green-400 flex-shrink-0" />
                <div className="flex-1">
                  <h3 className="font-semibold mb-2">Android 설치 방법</h3>
                  <ol className="space-y-2 text-sm text-muted-foreground">
                    <li className="flex gap-2">
                      <span className="font-bold text-green-400">1.</span>
                      <span>Chrome 브라우저로 이 페이지를 여세요</span>
                    </li>
                    <li className="flex gap-2">
                      <span className="font-bold text-green-400">2.</span>
                      <span>우측 상단 <strong>메뉴 (⋮)</strong> 를 탭하세요</span>
                    </li>
                    <li className="flex gap-2">
                      <span className="font-bold text-green-400">3.</span>
                      <span><strong>"홈 화면에 추가"</strong> 또는 <strong>"앱 설치"</strong> 를 선택하세요</span>
                    </li>
                    <li className="flex gap-2">
                      <span className="font-bold text-green-400">4.</span>
                      <span><strong>"설치"</strong> 버튼을 탭하세요</span>
                    </li>
                  </ol>
                  <div className="mt-3 p-2 rounded bg-cyan-500/10 border border-cyan-500/30">
                    <p className="text-xs text-cyan-400">
                      💡 <strong>팁:</strong> 주소창 하단에 설치 배너가 자동으로 나타날 수도 있습니다.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Desktop 설치 안내 */}
          {!isMobile && (
            <div className="glass rounded-lg border border-white/10 bg-white/5 p-4 backdrop-blur-md">
              <div className="flex items-start gap-3">
                <Monitor className="h-6 w-6 text-purple-400 flex-shrink-0" />
                <div className="flex-1">
                  <h3 className="font-semibold mb-2">Desktop 설치 방법</h3>
                  <ol className="space-y-2 text-sm text-muted-foreground">
                    <li className="flex gap-2">
                      <span className="font-bold text-purple-400">1.</span>
                      <span>Chrome 또는 Edge 브라우저로 이 페이지를 여세요</span>
                    </li>
                    <li className="flex gap-2">
                      <span className="font-bold text-purple-400">2.</span>
                      <span>주소창 우측의 <strong>⊕ 설치 아이콘</strong> 을 클릭하세요</span>
                    </li>
                    <li className="flex gap-2">
                      <span className="font-bold text-purple-400">3.</span>
                      <span><strong>"설치"</strong> 버튼을 클릭하세요</span>
                    </li>
                  </ol>
                </div>
              </div>
            </div>
          )}
        </>
      )}

      {/* 설치 후 장점 */}
      <div className="glass rounded-lg border border-white/10 bg-white/5 p-4 backdrop-blur-md">
        <div className="flex items-start gap-3">
          <HelpCircle className="h-6 w-6 text-cyan-400 flex-shrink-0" />
          <div className="flex-1">
            <h3 className="font-semibold mb-2">앱 설치의 장점</h3>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li className="flex items-start gap-2">
                <span className="text-cyan-400">⚡</span>
                <span><strong>더 빠른 실행:</strong> 홈 화면에서 원클릭으로 즉시 실행</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-cyan-400">📵</span>
                <span><strong>오프라인 지원:</strong> 인터넷 없이도 이전 데이터 확인 가능</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-cyan-400">🔔</span>
                <span><strong>즉시 알림:</strong> 새로운 커밋이나 업데이트를 놓치지 않음</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-cyan-400">🎨</span>
                <span><strong>전체 화면:</strong> 주소창 없이 더 넓은 화면 사용</span>
              </li>
            </ul>
          </div>
        </div>
      </div>

      {/* 문제 해결 */}
      <div className="glass rounded-lg border border-white/10 bg-white/5 p-4 backdrop-blur-md">
        <h3 className="font-semibold mb-2">문제 해결</h3>
        <div className="space-y-2 text-sm text-muted-foreground">
          <details className="cursor-pointer">
            <summary className="font-medium text-foreground">설치 옵션이 보이지 않아요</summary>
            <div className="mt-2 ml-4 space-y-1">
              <p>• iOS: Safari 브라우저를 사용하세요 (Chrome/Firefox 불가)</p>
              <p>• Android: Chrome 브라우저를 사용하세요</p>
              <p>• Desktop: Chrome 또는 Edge 브라우저를 사용하세요</p>
              <p>• HTTPS 연결이 필요합니다 (현재 URL 확인)</p>
            </div>
          </details>
          <details className="cursor-pointer">
            <summary className="font-medium text-foreground">이미 설치했는데 보이지 않아요</summary>
            <div className="mt-2 ml-4 space-y-1">
              <p>• 홈 화면을 확인하세요</p>
              <p>• 앱 서랍(App Drawer)을 확인하세요</p>
              <p>• 기기를 재시작해보세요</p>
            </div>
          </details>
          <details className="cursor-pointer">
            <summary className="font-medium text-foreground">개발 환경에서 테스트하려면?</summary>
            <div className="mt-2 ml-4 space-y-1">
              <p>• 프로덕션 빌드가 필요합니다: <code className="bg-black/30 px-1">npm run build</code></p>
              <p>• HTTPS로 배포되어야 합니다</p>
              <p>• 로컬 개발 서버(HTTP)에서는 설치 불가</p>
            </div>
          </details>
        </div>
      </div>
    </div>
  );
}
