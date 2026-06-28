## 정의

이 프로젝트는 '소설가가 되자(小説家になろう)'와 '카쿠요무(カクヨム)'의 에피소드를 다운로드하여 epub 형식으로 만드는 프로젝트입니다.

GitHub Actions(Workflow)와 GitHub Pages, 그리고 Personal Access Token (classic)을 이용하여 오직 git 환경만으로도 실행 가능하게 제작되었습니다.

> ⚠️ **면책 조항:** 본 프로그램을 이용함으로써 발생하는 모든 불이익에 대해 개발자는 책임을 지지 않습니다.

## 사용법

1. GitHub에서 새 프로젝트(Repository)를 만들고, 본 프로젝트와 똑같은 구조와 코드로 채워 넣습니다. (※ `index.html` 파일은 복사하지 않아도 됩니다.)
2. 프로젝트 설정을 **Public**으로 변경합니다. (무료로 GitHub Actions를 실행하기 위함입니다.)
3. GitHub 프로필 Settings -> Developer Settings에서 **Personal Access Token (classic)**을 생성합니다.
   * 💡 토큰 생성 시 **`repo`**와 **`workflow`** 권한을 반드시 체크해야 합니다.
4. [syosetu-downloader 서비스 페이지](https://minekmj.github.io/syosetu-downloader/)에 접속합니다.
5. 페이지 안내에 따라 생성한 개인 액세스 토큰과 다운로드할 소설 정보를 입력한 뒤 실행합니다.
6. 완료되면 epub 파일이 포함된 zip 압축 파일이 웹 브라우저를 통해 자동으로 다운로드됩니다.
