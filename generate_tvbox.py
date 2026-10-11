name: JSON Build & API Check

on:
  schedule:
    - cron: "0 17 * * *" # 北京时间凌晨1点
  push:
    paths:
      - 'KVideo-config.json'
  workflow_dispatch:
    inputs:
      api_name:
        description: '搜索关键字'
        default: '1'

jobs:
  build-and-check:
    runs-on: ubuntu-latest
    permissions:
      contents: write

    steps:
      - uses: actions/checkout@v4

      # 关键步骤：每次检测前，自动从上游拉取最新的采集源列表覆盖本地
      - name: Sync latest config from upstream
        run: |
          curl -sSL "https://raw.githubusercontent.com/puppet680/KVideo-config/main/KVideo-config.json" -o KVideo-config.json || true
          curl -sSL "https://raw.githubusercontent.com/puppet680/KVideo-config/main/check_api.js" -o check_api.js || true

      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: 18

      - name: Install dependencies
        run: npm install axios

      - name: Run Check Script
        run: |
          SEARCH_KEY="${{ github.event.inputs.api_name || '斗罗大陆' }}"
          node check_api.js "$SEARCH_KEY"

      - name: Generate TVBox Config
        run: |
          node -e '
            const fs = require("fs");
            const crypto = require("crypto");

            try {
              if (!fs.existsSync("lite.json")) {
                console.error("lite.json 不存在，跳过转换");
                process.exit(0);
              }

              const raw = fs.readFileSync("lite.json", "utf-8");
              const parsed = JSON.parse(raw);
              const list = Array.isArray(parsed) ? parsed : (parsed.sites || parsed.data || []);

              const sites = [];
              for (const item of list) {
                const apiUrl = item.baseUrl || item.api || item.url;
                const name = item.name || "未命名接口";

                if (!apiUrl || typeof apiUrl !== "string") continue;

                const key = "cms_" + crypto.createHash("md5").update(apiUrl).digest("hex").slice(0, 8);

                sites.push({
                  key: key,
                  name: name,
                  type: 1,
                  api: apiUrl,
                  searchable: 1,
                  quickSearch: 1,
                  filterable: 1
                });
              }

              const tvboxConfig = {
                spider: "",
                wallpaper: "https://picsum.photos/1920/1080",
                sites: sites
              };

              fs.writeFileSync("tvbox.json", JSON.stringify(tvboxConfig, null, 2), "utf-8");
              console.log(`成功生成 tvbox.json，共包含 ${sites.length} 个可用源`);
            } catch (err) {
              console.error("生成 TVBox 配置失败:", err);
            }
          '

      - name: Commit and push changes
        run: |
          git config --global user.name "github-actions[bot]"
          git config --global user.email "github-actions[bot]@users.noreply.github.com"
          git add KVideo-config.json check_api.js adult.json lite.json report.md tvbox.json
          git commit -m "chore: 同步上游并更新 TVBox 配置 [$(date +'%Y-%m-%d %H:%M')]" || echo "No changes"
          git push
