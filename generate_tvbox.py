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

      # 自动同步上游最新配置
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

      - name: Generate TVBox Configs (Standard & Adult)
        run: |
          node -e '
            const fs = require("fs");
            const crypto = require("crypto");

            function extractSites(filePath, isAdult = false) {
              if (!fs.existsSync(filePath)) return [];
              const raw = fs.readFileSync(filePath, "utf-8");
              const parsed = JSON.parse(raw);
              const list = Array.isArray(parsed) ? parsed : (parsed.sites || parsed.data || []);
              
              const res = [];
              for (const item of list) {
                const apiUrl = item.baseUrl || item.api || item.url;
                if (!apiUrl || typeof apiUrl !== "string") continue;

                // 若有状态字段，剔除失效接口
                if (item.status && (item.status.includes("❌") || item.status.includes("失效") || item.status.includes("超时"))) {
                  continue;
                }

                const prefix = isAdult ? "cms_a_" : "cms_";
                const displayName = isAdult ? `[18+] ${item.name || "精选"}` : (item.name || "未命名");
                const key = prefix + crypto.createHash("md5").update(apiUrl).digest("hex").slice(0, 8);

                res.push({
                  key: key,
                  name: displayName,
                  type: 1,
                  api: apiUrl,
                  searchable: 1,
                  quickSearch: 1,
                  filterable: 1
                });
              }
              return res;
            }

            try {
              const liteSites = extractSites("lite.json", false);
              const adultSites = extractSites("adult.json", true);

              // 1. 生成纯净版 tvbox.json
              const standardConfig = {
                spider: "",
                wallpaper: "https://picsum.photos/1920/1080",
                sites: liteSites
              };
              fs.writeFileSync("tvbox.json", JSON.stringify(standardConfig, null, 2), "utf-8");

              // 2. 生成合并完整版 tvbox-adult.json（去重合并）
              const allSites = [...liteSites];
              const seen = new Set(liteSites.map(s => s.api));
              for (const s of adultSites) {
                if (!seen.has(s.api)) {
                  seen.add(s.api);
                  allSites.push(s);
                }
              }

              const fullConfig = {
                spider: "",
                wallpaper: "https://picsum.photos/1920/1080",
                sites: allSites
              };
              fs.writeFileSync("tvbox-adult.json", JSON.stringify(fullConfig, null, 2), "utf-8");

              console.log(`生成完成: tvbox.json(${liteSites.length}个) | tvbox-adult.json(${allSites.length}个)`);
            } catch (err) {
              console.error("生成配置失败:", err);
            }
          '

      - name: Commit and push changes
        run: |
          git config --global user.name "github-actions[bot]"
          git config --global user.email "github-actions[bot]@users.noreply.github.com"
          git add KVideo-config.json check_api.js adult.json lite.json report.md tvbox.json tvbox-adult.json
          git commit -m "chore: 同步上游并更新标准与扩展 TVBox 配置 [$(date +'%Y-%m-%d %H:%M')]" || echo "No changes"
          git push
