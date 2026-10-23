# 怎么用 GitHub Actions 跑 riva XNU 编译

这份指南给【第一次用 GitHub / GitHub Actions】的人。跟着做就行。目标:把本机这份
`riva-ios/` 推上 GitHub,然后让 GitHub 自动帮你编译 XNU 内核。

时间:第一次约 30–60 分钟(含注册、装工具、推送)。之后每次改补丁,一键重跑。

---

## 第 0 步:搞清三样东西的作用

| 东西 | 是什么 | 你要做的 |
|------|--------|----------|
| **GitHub 账号** | 云上的代码托管 | 免费注册一个 |
| **GitHub 仓库(repo)** | 装代码的一个"文件夹",在云上 | 建一个,把 `riva-ios/` 推上去 |
| **GitHub Actions** | GitHub 自带的"自动执行任务" | 我这个 `xnu.yml` 文件就是任务脚本,推到仓库就自动生效 |

`riva-ios/.github/workflows/xnu.yml` 就是那个自动任务。它会在 GitHub 的 **macOS
编译机**上:拉 XNU 源码 → 套上你的 riva 补丁 → 编译出内核 → 打包成可下载的
"artifact(产物)"。

---

## 第 1 步:注册 GitHub 账号(若没有)

- 打开 https://github.com/signup
- 填邮箱、设密码、起用户名,按提示完成验证。
- 记住你的 **用户名** 和 **邮箱**。

## 第 2 步:装 git(已装则跳过)

- 你本机已有 `git 2.43`,可跳过。
- (装 GitHub Desktop 的也可以——它免命令行,见文末"可选 B")。

## 第 3 步:告诉 git 你是谁(只需一次)

打开终端,执行(把名字/邮箱换成你的):

```bash
git config --global user.name  "你的用户名"
git config --global user.email "你的注册邮箱"
```

## 第 4 步:把本机 `riva-ios/` 变成一个 git 仓库

在终端进到项目目录:

```bash
cd /home/midori/riva_iosport/riva-ios
git init                                  # 变成 git 仓库
git add -A                                # 把当前所有文件都加进来
git commit -m "riva ios port — ci + tools seed"   # 打一个提交
```

> 说明:`git init` = 告诉 git"从这里开始管理版本";`git add -A` = 把文件放进
> 暂存区;`git commit` = 拍一张"快照"。Actions 依托的就是这些快照。

## 第 5 步:在 GitHub 上建一个空仓库

网页方式:
1. 登录 GitHub → 点右上角 **+** → **New repository**。
2. 填 **Repository name**,比如 `riva-ios`。
3. **Public / Private** 随便选(Public 免费无限量 Actions 更好跑)。
4. 别勾选"Add a README / .gitignore / license"(会有冲突),保持全空。
5. 点 **Create repository**。

## 第 6 步:把本地仓库推到 GitHub

网页方式给的那段代码里,选 **HTTPS** 那一行(别选 SSH)。通常长这样:

```bash
git remote add origin https://github.com/你的用户名/riva-ios.git
git branch -M main
git push -u origin main
```

- 第一条 `add origin` = 告诉 git"远端仓库的地址";
- 第三条 `push` = 把本地推上去。第一次会弹出浏览器窗口让你**登录授权**。
- 授权通过后,会自动触发 Actions(因为推送了)。

## 第 7 步:找到并运行 Actions

推送完成后,网页上:
1. 仓库页面点上方 **Actions** 标签。
2. 会看到 `riva-xnu-build` 这个工作流。
3. 我这条是**手动触发**(`workflow_dispatch`)+ 自动触发两个都开了。若没自动跑,
   点该工作流 → 右边 **Run workflow** 绿色按钮 → 确认弹出的默认参数 → 点 **Run workflow**。
   参数说明:
   - `macos_version` 默认 `13.5`(xnu-8796 对应) —— 保持默认。
   - `kernel_config` 默认 `DEVELOPMENT` —— 保持默认。
   - `machine_config` 默认 `RIVA` —— 保持默认(**这就是 riva**)。
4. 点进去看执行进度(黄=运行中 / 绿=成功 / 红=失败)。

第一次跑:**预计会失败**,原因很明确——现在 `xnu/patches/` 里还只有说明、没有
真正可套进去的补丁,`MACHINE_CONFIG=RIVA` 也还没有对应的 riva 编译配置。**这是
预期内的,别慌。** 目的是先把整条"编译管线"打通、验证 GitHub 环境能正确拉源码和
跑构建。

## 第 8 步:下载编译产物(artifact)

编译(哪怕部分成功)后,页面底部会有两块可下载的产物:
- **xnu-kernel** —— 编译出来的内核(Mach-O)。
- **xnu-buildtree** —— 打补丁后的源码 + 生成头,供本地单文件重编译调试。

点蓝底白字的产物卡片 → 右上角 **下载**。拿到 `xnu-kernel` 后,下一步就是你在
本机用:

```bash
python3 tools/mkpayload-riva.py --kernel <xnu内核文件> --adt device/riva-adt.dtb -o payload.bin
```

打包成能在 shim 里加载的 payload。

---

## 之后每次改动补丁怎么重新跑

`on.push.paths` 里我写的是 `xnu/patches/**`,意思是:**只要 `xnu/patches/` 目录
里的文件有变更并推送,就会自动重新编译**。所以日常循环是:

```bash
# 1) 写/改一个 riva 补丁到 xnu/patches/*
# 2) 提交并推送
git add -A
git commit -m "riva: 新增 GICv2 补丁"
git push
# 3) GitHub 自动重跑 → 回 Actions 看结果/下载内核
```

想手动重跑(不改代码)就去 Actions → Run workflow。

---

## 报错排查(按提示对号入座)

| 现象 | 原因 | 解决办法 |
|------|------|----------|
| `Failed to connect` / `Authentication failed` 在 push | 没授权或密码错 | 用 GitHub 生成 **Personal Access Token**,push 时用户名填账号、密码填 token;或用浏览器授权登录 |
| `remote origin already exists` | 重复 `add origin` | 改执行 `git remote set-url origin <新地址>` |
| Actions 里看不到工作流 | `xnu.yml` 还没推上去 / 路径不对 | 确认文件在 `riva-ios/.github/workflows/xnu.yml`(必须这个路径);推上去后再刷新 Actions |
| 跑了但红叉 | `RIVA` 配置/补丁还没有 | **预期内**。参考 `xnu/patches/RIVA_PORT_MAP.md`,先补 `0001-riva-machine-add.patch` 这类地基补丁 |
| 编译很久没反应 | macOS 编译机在装依赖 | 正常;首次 20–40 分钟,别关页面 |
| 免费额度用了怎么办 | public 仓库 Actions 免费用量大 | 保持仓库 Public;或改用 `self-hosted` 编译机(进阶) |

---

## 可选 A:用命令行工具 `gh`(比网页方便)

本机没装。装法(Ubuntu/Debian):

```bash
sudo apt-get update
sudo apt-get install -y gh
gh auth login            # 按提示用浏览器向导登录
```

之后建仓、推、跑一条龙:

```bash
cd /home/midori/riva_iosport/riva-ios
git init && git add -A && git commit -m "riva ios port seed"
gh repo create riva-ios --public --source=. --push
gh workflow run riva-xnu-build.yml      # 手动触发
gh run watch                           # 实时看进度
```

## 可选 B:用 GitHub Desktop(完全不碰命令行)

下载:https://desktop.github.com 。流程:File → Add local repository → 选
`riva-ios` → Publish repository → 推上去后 GitHub 网页接着按第 7 步走。

---

## 关键提醒(避免 30 分钟白忙)

1. **先把补丁补上再指望成功**:`xnu/patches/` 现在只有规划,没有真正能套的 diff。
   第一次跑主要是验证管线;真正要过,至少写一个 `0001-riva-machine-add.patch`。
2. **文件必须放在 `.github/workflows/` 下**,否则 GitHub 不认。
3. **Roles 别给错**:Actions 只在"推送到 GitHub 后"才能用,本地不会跑。
4. 这一套只解决了——**如何让 GitHub 自动编译 XNU**。真正"让内核能开机"的
   驱动补丁(见 `RIVA_PORT_MAP.md` 的 🔴 那 5 个)仍需你自己或内核开发者去写。

如果需要,我可以下一步就直接帮你把 `0001-riva-machine-add.patch` 的地基 diff
写出来,让这个 CI 第一次就能编出一个"属于 riva 的 XNU 内核"。