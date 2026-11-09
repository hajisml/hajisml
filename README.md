<!-- Personal profile banner-->
<h1 align="center">
    <img src=".github/hajisml_banner.png" alt="Profile banner"/>
</h1>

<!-- Typing svg presentation-->
<div align="center">
    <a href="https://hajisml.github.io">
        <picture>
            <source media="(prefers-color-scheme: dark)" srcset="https://readme-typing-svg.demolab.com?font=Fira+Sans&size=22&duration=4000&pause=1000&color=F0F6FC&center=true&vCenter=true&width=410&lines=We+%CE%94re+%CD%B6ot+%CD%B2he+%CF%9E%CE%B1%CF%BBe%2C+I'%CF%BB+%CE%94+%CF%BB%CE%B1rti%CE%B1%CE%B7;-+lil+W%CE%B1y%CE%B7e" />
            <img src="https://readme-typing-svg.demolab.com?font=Fira+Sans&size=22&duration=4000&pause=1000&color=1F2328&center=true&vCenter=true&width=410&lines=We+%CE%94re+%CD%B6ot+%CD%B2he+%CF%9E%CE%B1%CF%BBe%2C+I'%CF%BB+%CE%94+%CF%BB%CE%B1rti%CE%B1%CE%B7;-+lil+W%CE%B1y%CE%B7e" alt="We are not the same, I'm a Martian — Lil Wayne" />
        </picture>
    </a>
</div>
<!-- Socials-->
<div align="center" >
    <a href="https://dev.to/hajisml"><img alt="DEV.to" src="https://img.shields.io/badge/DEV-000000?style=for-the-badge&logo=dev.to&logoColor=white"></a>
    <a href="https://linkedin.com/in/hajisml"><img alt="LinkedIn" src="https://img.shields.io/badge/LinkedIn-0A66C2?style=for-the-badge&logo=linkedin&logoColor=white"></a>
    <a href="https://www.youtube.com/@hajsml"><img alt="YouTube" src="https://img.shields.io/badge/YouTube-FF0000?style=for-the-badge&logo=youtube&logoColor=white"></a>
    <a href="https://www.twitch.tv/hajisml"><img alt="Twitch" src="https://img.shields.io/badge/Twitch-6441A4?style=for-the-badge&logo=twitch&logoColor=white"></a>
    <a href="https://x.com/hajisml"><img alt="X" src="https://img.shields.io/badge/Twitter-000000?style=for-the-badge&logo=x&logoColor=white"></a>
    <a href="https://mastodon.social/@hajisml"><img alt="Mastodon" src="https://img.shields.io/badge/Mastodon-6364FF?style=for-the-badge&logo=mastodon&logoColor=white"></a>
    <a href="https://substack.com/@hajisml"><img alt="Substack" src="https://img.shields.io/badge/Substack-orange?style=for-the-badge&logo=substack&logoColor=white"></a>
    <a href="https://t.me/hajisml"><img alt="Telegram" src="https://img.shields.io/badge/Telegram-blue?style=for-the-badge&logo=telegram&logoColor=white"></a>

<!-- Donations-->
<h6 align="center">₿ Bitcoin: bc1q9vyjnvxjkk40mjqf6cgkadklfxrug5ez6kzpxx<br>⚡Lightning: middleamber84@walletofsatoshi.com</h6>
</div><br>

<!-- About me server in Go -->
```go
package main

import (
	"encoding/json"
	"log/slog"
	"net/http"
	"time"
)

type Profile struct {
	Name      string   `json:"name"`
	Location  string   `json:"location"`
	Focus     []string `json:"focus"`
	Portfolio string   `json:"portfolio"`
}

func aboutMe(w http.ResponseWriter, _ *http.Request) {
	me := Profile{
		Name:      "Haji Ismael Ibrahim",
		Location:  "Lakecity",
		Focus:     []string{"Backend development", "Distributed systems", "Design"},
		Portfolio: "https://halim.is-a.dev",
	}

	w.Header().Set("Content-Type", "application/json")
	if err := json.NewEncoder(w).Encode(me); err != nil {
		log.Printf("write profile response: %v", err)
	}
}

func main() {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /about", aboutMe)

	server := &http.Server{
		Addr:              ":8080",
		Handler:           mux,
		ReadHeaderTimeout: 5 * time.Second,
	}
	if err := server.ListenAndServe(); err != nil {
		slog.Error("server", "err", err)
		os.Exit(1)
	}
}
```

<!-- About / Present -->
### 💡 Present

I'm **Haji Ismael Ibrahim**, a software engineer based in Lakecity. I build backend services with Go, Python, and well-tuned databases, with a focus on concurrency, socket programming, and distributed systems.

- 🧑🏾‍💻 Software Engineering Apprentice at [Zone01 Kisumu](https://zone01kisumu.ke).
- 🛠️ Building [Kamugram](https://github.com/hajisml/kamugram), a Swahili search engine and Telegram bot.
- 📚 Learning **full-stack Java development with Spring Boot**, from REST APIs to the front end.
- 🎨 Alongside code, I work on **brand identity and UI/UX** using Figma, GIMP, and Inkscape.
- 🌐 Explore my work at [halim-c4x.pages.dev](https://halim-c4x.pages.dev).

<!-- GitHub Statistics -->
### 📊 GitHub Statistics

<div align="center">
    <a href="https://github.com/hajisml?tab=repositories">
        <picture>
            <source media="(prefers-color-scheme: dark)" srcset="assets/overview-dark.svg" />
            <img src="assets/overview-light.svg" width="420" alt="GitHub overview: public repositories, stars, forks, and followers" />
        </picture>
        <picture>
            <source media="(prefers-color-scheme: dark)" srcset="assets/languages-dark.svg" />
            <img src="assets/languages-light.svg" width="420" alt="Languages by code size across public, owned, non-fork repositories" />
        </picture>
    </a>
</div>

<div align="center">
    <a href="https://git.io/streak-stats">
        <picture>
            <source media="(prefers-color-scheme: dark)" srcset="assets/streak-dark.svg" />
            <img src="assets/streak-light.svg" alt="Weekly GitHub contribution streak" />
        </picture>
    </a>
</div><br>

<!--START_SECTION:dev-excuse-->
<p align="center">
    <em>“The coffee mαchiηe ϟtopped workiηg todαy!”</em><br>
    <sub>— <a href="https://excuser-three.vercel.app">Excuser</a></sub>
</p>
<!--END_SECTION:dev-excuse-->

<details>
  <summary><b>⏳ View my WakaTime Statistics</b></summary>

<!--START_SECTION:waka-->
**📊 This Week I Spent My Time On**

```text
Programming Languages:
Bash                     29 mins           ████████████████████ 100.00 %
```

Last 7 days · Updated 2026-11-09 UTC · Source: [WakaTime](https://wakatime.com/@00a59a24-7f70-4add-abf2-ff361b4693fc)
<!--END_SECTION:waka-->

</details><br>

<details>
  <summary><b>🧠 View my Skills and Knowledge</b></summary><br>

<table>
    <tr><th>Area</th><th>Experience with</th></tr>
    <tr>
        <td>Languages</td>
        <td>
            <img src="https://img.shields.io/badge/Go-007D9C?style=for-the-badge&logo=go&logoColor=white" alt="Go" />
            <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
            <img src="https://img.shields.io/badge/SQL-4169E1?style=for-the-badge" alt="SQL" />
            <img src="https://img.shields.io/badge/JavaScript-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black" alt="JavaScript" />
            <img src="https://img.shields.io/badge/HTML5-E34F26?style=for-the-badge&logo=html5&logoColor=white" alt="HTML5" />
            <img src="https://img.shields.io/badge/CSS-663399?style=for-the-badge&logo=css&logoColor=white" alt="CSS" />
        </td>
    </tr>
    <tr>
        <td>Web and APIs</td>
        <td>
            <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" />
            <img src="https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white" alt="Flask" />
            <img src="https://img.shields.io/badge/Node.js-339933?style=for-the-badge&logo=nodedotjs&logoColor=white" alt="Node.js" />
            <img src="https://img.shields.io/badge/Deno-000000?style=for-the-badge&logo=deno&logoColor=white" alt="Deno" />
            <img src="https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB" alt="React" />
            <img src="https://img.shields.io/badge/REST_APIs-0969DA?style=for-the-badge" alt="REST APIs" />
        </td>
    </tr>
    <tr>
        <td>Data and Infrastructure</td>
        <td>
            <img src="https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL" />
            <img src="https://img.shields.io/badge/MongoDB-00684A?style=for-the-badge&logo=mongodb&logoColor=white" alt="MongoDB" />
            <img src="https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white" alt="Redis" />
            <img src="https://img.shields.io/badge/SQLite_FTS5-003B57?style=for-the-badge&logo=sqlite&logoColor=white" alt="SQLite FTS5" />
            <img src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker" />
            <img src="https://img.shields.io/badge/Podman-892CA0?style=for-the-badge&logo=podman&logoColor=white" alt="Podman" />
            <img src="https://img.shields.io/badge/AWS-232F3E?style=for-the-badge" alt="AWS" />
            <img src="https://img.shields.io/badge/Linux-FCC624?style=for-the-badge&logo=linux&logoColor=black" alt="Linux" />
        </td>
    </tr>
    <tr>
        <td>Engineering Practices</td>
        <td>Distributed systems · Concurrency · Socket programming · CI/CD · Code review · Mentorship</td>
    </tr>
    <tr>
        <td>Design</td>
        <td>
            <img src="https://img.shields.io/badge/Figma-F24E1E?style=for-the-badge&logo=figma&logoColor=white" alt="Figma" />
            <img src="https://img.shields.io/badge/GIMP-5C5543?style=for-the-badge&logo=gimp&logoColor=white" alt="GIMP" />
            <img src="https://img.shields.io/badge/Inkscape-000000?style=for-the-badge&logo=inkscape&logoColor=white" alt="Inkscape" />
            <br>Brand identity · UI/UX
        </td>
    </tr>
    <tr>
        <td>Currently Learning</td>
        <td>
            <img src="https://img.shields.io/badge/Java-ED8B00?style=for-the-badge" alt="Java" />
            <img src="https://img.shields.io/badge/Spring_Boot-6DB33F?style=for-the-badge&logo=springboot&logoColor=white" alt="Spring Boot" />
            <br>Full-stack Java development, from REST APIs to the front end
        </td>
    </tr>
    <tr>
        <td>Education</td>
        <td>Software Engineering Apprentice at <a href="https://zone01kisumu.ke">Zone01 Kisumu</a> · B.Sc. Software Development, KCA University</td>
    </tr>
</table>

</details><br>

<!-- Updates -->
<details>
  <summary><b>🚀 Updates</b></summary><br>
    <ul>
        <li>🛠️ Working on <a href="https://github.com/hajisml/kamugram">Kamugram!</a></li>
        <li>🧑🏾‍💻 Apprentice at <a href="https://zone01kisumu.ke">Zone01 Kisumu</a></li>
        <li><a href="https://wakatime.com/@00a59a24-7f70-4add-abf2-ff361b4693fc"><img src="https://wakatime.com/badge/user/00a59a24-7f70-4add-abf2-ff361b4693fc.svg" alt="Total time coded since Nov 25 2024" /></a></li>
    </ul>
</details><br>

<!-- Footer -->
<div align="center">
<h6 align="center">- Mαrtiαηϟ VϞ Gobliηϟ -</h6>
</div>
