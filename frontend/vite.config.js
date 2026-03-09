import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// 카카오맵 SDK 스크립트 src의 %VITE_KAKAO_MAP_KEY% 를 환경변수로 치환하는 플러그인
function kakaoMapKeyPlugin(env) {
  return {
    name: 'kakao-map-key',
    transformIndexHtml(html) {
      console.log(env.VITE_KAKAO_MAP_KEY, 'env.VITE_KAKAO_MAP_KEYenv.VITE_KAKAO_MAP_KEY')
      return html.replace(/%VITE_KAKAO_MAP_KEY%/g, env.VITE_KAKAO_MAP_KEY || '')
    },
  }
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  console.log("asdfadsfgdaf", env.VITE_API_BASE_URL, env.VITE_KAKAO_MAP_KEY, 'env.VITE_KAKAO_MAP_KEYenv.VITE_KAKAO_MAP_KEY')
  return {
    plugins: [react(), kakaoMapKeyPlugin(env)],
    server: {
      port: 3000,
      host: true,
      allowedHosts: true,
    },
  }
})
