Senga kerak bo‘lgan loyiha: Local AI Software Engineer Agent
Sen aytayotgan g‘oya shunchaki kod yozadigan chatbot emas. Sen yaratmoqchi bo‘lgan tizim — har qanday dasturiy loyihani tahlil qiladigan, uning arxitekturasini tushunadigan, bog‘lanishlarini xaritada ko‘rsatadigan, zaifliklarini topadigan va kichik lokal LLM yordamida loyihani o‘zgartira oladigan AI muhandis.

Men topgan eng muhim xulosa: bu g‘oyaning ko‘p qismlari allaqachon alohida-alohida yaratilgan. Hatto ayrim loyihalar bir nechta qismini birlashtirgan. Shuning uchun eng to‘g‘ri yo‘l — mavjud ishlanmalarni o‘rganib, ularning kuchli tomonlarini bitta tizimga birlashtirish va yetishmayotgan qismlarini ishlab chiqish.

Masalan, GitHub'dagi codeGRAPH lokal Ollama modeli bilan kod bazasini tahlil qilish va bog‘lanishlarini ko‘rsatishga qaratilgan. Aider esa butun repository haqida ixcham xarita tuzib, aynan kerakli kod kontekstini modelga beradi. Codeknow AST asosida kod bazasining bilim grafigini yaratadi. 


GitHub
+2



Demak, sen uchun asosiy masala noldan yana bir coding agent yozish emas. Kod haqidagi aniq bilim, agentning ish rejasi, maxsus vositalar, tekshiruv va xotirani shunday birlashtirish kerakki, kichik model ham murakkab vazifalarni boshqara olsin.
1. Xitoydagi qonun masalasi — avval aniqlashtirib olaylik
2026-yil 16-oktabr kuni Xitoy ayrim sun’iy intellekt texnologiyalarining eksportini nazorat qilish bo‘yicha yangi taklifni e’lon qildi. Taklif yirik AI modellari, agentlar, chip dizayni va boshqa texnologiyalarni ham qamrab oladi. Bu barcha ochiq modellarni odamlar yuklab olishi yoki kompyuterida ishlatishini taqiqlash bilan bir xil emas. Reuters xabariga ko‘ra, ommaga ochiq texnologiyalar uchun ko‘p jihatdan istisnolar ko‘zda tutilgan; taklif bo‘yicha jamoatchilik fikrini bildirish muddati 2026-yil 15-noyabrgacha. 


Reuters
+1



Shunga qaramay, sening xavotiring asosli: Claude yoki OpenAI API ishlamay qolsa, asosiy coding ishlaring to‘xtab qolmasligi kerak. Buni hal qilish uchun faqat modelni yuklab qo‘yish yetmaydi. Modelning loyihani qanday o‘rganishi, kerakli kodni qanday topishi, o‘zgarishni qanday tekshirishi va xatoni qanday tuzatishi ham hal qiluvchi rol o‘ynaydi.
2. GitHub'dagi mavjud loyihalar: qaysilari sening g‘oyangga yaqin?
Men topgan loyihalarni vazifalariga qarab ajratdim. Muhim farq: ayrimlari kod bazasini xaritalaydi, ayrimlari kod yozadi, boshqalari esa xavfsizlik yoki hujjatlar bilan ishlaydi. Ularning hammasi bir xil muammoni hal qilmaydi.
A. Kod bazasini tushunish va arxitektura xaritasini yaratish









1. GRASP
Eng yaqin umumiy yechimlardan biri
Kod tahlili · grafik xarita · MCP · xavfsizlik

Loyiha sahifasida 35 ta dasturlash tili, interaktiv arxitektura xaritalari, git o‘zgarishlarining ta’sirini tahlil qilish, ORM bog‘lanishlari, test qamrovi va zaifliklarni aniqlash vositalari ko‘rsatilgan. MCP serveri orqali boshqa AI agentlariga ham shu vositalarni taqdim eta oladi. 


GitHub
+1



Senga nima beradi? Frontend, backend va ma’lumotlar bazasi orasidagi bog‘lanishlarni ko‘rsatadigan tahlil qatlamiga yaxshi boshlang‘ich nuqta.

Cheklovi: Bu juda yosh loyiha. GitHub sahifasida ko‘rsatilgan litsenziyasi Elastic License 2.0: o‘zgartirish va o‘zingda ishlatish mumkin, ammo uni boshqa nom ostida yoki boshqariladigan hosting xizmati sifatida tarqatishga cheklovlar bor. Ishlatishdan oldin litsenziyaning aynan rejangga tegishli bandlarini tekshir. 


GitHub



Repository: ashfordeOU/grasp












2. codeGRAPH — Codebase Cartographer

Mahalliy LLM · LangGraph · kod xaritasi

Bu sen tasvirlagan narsaga juda o‘xshash konsepsiya: repository fayllarini tahlil qilish, dependency graph yaratish, alohida faylni tushuntirish va butun loyiha haqida savollarga javob berish. Masalan, “engine.py o‘zgarsa nima buzilishi mumkin?” yoki “API dan database gacha bo‘lgan oqimni ko‘rsat” kabi savollar uchun yaratilgan. Ollama orqali lokal modellar bilan ishlaydi. 


GitHub



Muhim cheklovi: README’da bog‘lanishlarni aniqlashning bir qismi model tahliliga asoslangan; Python uchun AST orqali qo‘shimcha tekshiruv mavjud. Dynamic importlar kabi holatlar esa muammo sifatida ko‘rsatilgan. Shuning uchun natijani avtomatik ravishda mukammal arxitektura xaritasi deb qabul qilish mumkin emas. 


GitHub



Senga nima beradi? Loyiha arxitekturasini lokal AI bilan vizual ko‘rsatishning ishlaydigan boshlang‘ich namunasi.












3. Codeknow

AST · bilim grafigi · o‘zgarish ta’siri

Bu loyiha kodni shunchaki matn sifatida emas, balki funksiyalar, klasslar, modullar va ular orasidagi munosabatlar grafigi sifatida tahlil qiladi. Tree-sitter asosida 25 dan ortiq til uchun tahlilni, impact orqali o‘zgarish ta’sirini, test-impact orqali ta’sirlanishi mumkin bo‘lgan testlarni, security orqali manbadan xavfli nuqtagacha bo‘lgan yo‘llarni tekshirishni taklif qiladi. 


GitHub



Senga nima beradi? AI modelidan oldin loyiha haqida aniqroq, qayta tekshiriladigan strukturaviy ma’lumot tayyorlash.

Cheklovi: Bu to‘liq mustaqil coding agent emas. Asosiy kuchi — kodni tahlil qilish va o‘zgarishning ta’sirini baholash; kompleks funksiyani boshidan oxirigacha ishlab chiqish uchun alohida agent kerak bo‘ladi.



Bu uchta loyiha ichida GRASP ko‘proq funksiyalarni bitta joyga yig‘ishga uringan; codeGRAPH lokal model bilan ishlash tajribasini ko‘rsatadi; Codeknow esa LLM’ga to‘liq ishonib qolmasdan kod strukturasini dasturiy ravishda tahlil qilishni ko‘zlaydi.
B. Haqiqiy kod yozish va o‘zgartirish agentlari









4. Aider

Repository konteksti · kod tahrirlash · git

Aider’ning eng foydali g‘oyasi — RepoMap. U butun loyihadagi muhim klasslar, funksiyalar, imzolar va bog‘lanishlardan ixcham xarita yaratadi. So‘ng joriy vazifa uchun muhim qismlarni tanlab, modelga uzatadi. Bu katta loyihani to‘liq promptga joylashtirishdan ancha oqilona. Aider lokal Ollama modellari bilan ham ishlay oladi. 


GitHub
+1



Senga nima beradi? Kichik modelga qaysi faylga murojaat qilish, mavjud arxitektura asosida kod yozish va o‘zgarishlar bilan ishlashni tashkil qilish uchun tayyor mexanizm.

Cheklovi: RepoMap butun loyiha haqida mukammal, barcha texnologik qatlamlarni qamrab oluvchi bilim grafigi emas. U katta loyihani modelga tushuntirishga yordam beradigan ixcham kontekst xaritasi.












5. OpenHands

Mustaqil coding ish jarayoni · terminal · fayllar · testlar

OpenHands agentga vazifani bajarish uchun vositalar beradi: kodni ko‘rish, fayllarni o‘zgartirish, buyruqlarni bajarish va test natijalariga qarab keyingi qadamni tanlash. Rasmiy hujjatlar Ollama, LM Studio, vLLM va boshqa lokal model serverlariga ulanishni ko‘rsatadi. Shu bilan birga, lokal modellar imkoniyati cheklangan bo‘lishi mumkinligi ham qayd etilgan. 


GitHub
+1



Senga nima beradi? Faqat javob qaytaradigan chatbot emas, balki kod ustida amaliy ish bajaruvchi agent uchun asos.

Cheklovi: OpenHands mavjud lokal modelning o‘zi yaxshi rejalashtiradi yoki murakkab loyihani to‘liq tushunadi degani emas. Bunga alohida kontekst, testlar va vazifalarni boshqarish qatlami kerak.












6. Continue

IDE integratsiyasi · kod indekslash · kontekst qidirish

Continue kod bazasini indekslash va fayllardagi o‘zgarishlarni hisobga olgan holda indeksni qayta ishlash mexanizmlariga ega. Indekslar ichiga embeddinglar, to‘liq matnli qidiruv hamda fayl darajasidagi ixcham ma’lumotlar kirishi mumkin. 


GitHub



Senga nima beradi? O‘z agentingni noldan IDE ichiga joylashtirish o‘rniga, kod qidirish va muharrirga ulanish kabi qismlarni o‘rganish uchun asos.

Cheklovi: IDE yordamchisi va indekslashning o‘zi butun arxitekturani kafolatli tushunadigan mustaqil muhandis emas.



Shu yerda asosiy farqni eslab qol
Aider, OpenHands va Continue kabi loyihalar modelga vazifani bajarish uchun muhit va vositalar beradi. Codeknow, codeGRAPH va GRASP esa kod bazasi haqida kontekst, strukturaviy bilim yoki tahlil vositalarini beradi.

Sening maqsading uchun aynan shu ikki turdagi tizimni birlashtirish zarur.
C. Kod xavfsizligi va aniq dasturiy tahlil









7. Semgrep

Kod ichidagi xato naqshlari, xavfsizlik muammolari va kod standartlarini tekshiradi. AI taxmin qilgan “bu joy zaif bo‘lishi mumkin” degan fikrni aniq qoidalar bilan tekshirishga yordam beradi. Lekin Semgrep’ning Community Edition versiyasida ayrim ko‘p-faylli va kengroq tahlil imkoniyatlari cheklangan. 


GitHub















8. CodeQL

Dastur kodini so‘rovlar yordamida tahlil qiladi. Ayniqsa, foydalanuvchi kiritgan ma’lumotning qayerdan kelishi va qaysi funksiyalar orqali xavfli operatsiyaga yetib borishini kuzatish muhim. Bu sen xohlagan “bog‘lanishlar va ehtimoliy zaifliklar” xaritasi uchun foydali qatlam. 


CodeQL
+1















9. ast-grep

Oddiy matn qidirishdan farqli ravishda kodning sintaktik tuzilishiga qarab topish va o‘zgartirish imkonini beradi. Masalan, muayyan naqshga mos keladigan funksiyalar chaqiruvlarini topish yoki strukturaviy refaktoring qilish. 


GitHub






Bu vositalarning bitta katta foydasi bor: sen yaratadigan tizim barcha xulosalarni LLM’dan so‘rab o‘tirmaydi. Kodni sintaksis, ma’lumot oqimi, bog‘lanish va xavfsizlik nuqtayi nazaridan mustaqil tekshira oladi.
D. Skill, hujjatlar va oldingi tajribadan foydalanish
Loyiha	Nima uchun kerak?
Agent Skills	Har bir vazifa uchun alohida SKILL.md, yo‘riqnoma, skript va ma’lumotlarni paketlash formati.  GitHub
Context7	Kutubxonalarning dolzarb, versiyaga mos hujjatlari va kod misollarini agentga berish.  Context7 MCP
CL-Agent	Coding sessiyalarini qayd etish, takror ijro qilish, foydali qoidalarni ajratib olish va natijani sinashga qaratilgan tajribaviy tizim. Bu o‘zi to‘liq coding agent emas.  GitHub
Bu qismlarni ham birlashtirish kerak. Ammo “skill” shunchaki uzun prompt degani emas. Yaxshi skill o‘zida kerakli shartlar, ish tartibi, bajariladigan skriptlar, misollar va tekshiruvlar to‘plamini saqlaydi.

Masalan, add-backend-endpoint skill quyidagilarni bajarishga yo‘naltirishi mumkin: avval mavjud routing tuzilishini topish, autentifikatsiya qoidalarini aniqlash, tegishli servis va ma’lumotlar modelini o‘rganish, mavjud loyihaning uslubiga mos kod yozish, test qo‘shish va natijani tekshirish.

3. Demak, sen aytgan agent allaqachon tayyormi?
Qisman. To‘liq, kafolatli ko‘rinishda esa men tekshirgan manbalarda sen aytgan barcha talablarni birlashtirgan va lokal 8B modelga Opus darajasidagi universal dasturlash sifatini ishonchli ta’minlaydigan yechimni tasdiqlay olmadim.

Eng yaqin variantlar quyidagicha:
- GRASP — strukturaviy tahlil, turli grafiklar va MCP vositalarining keng to‘plamiga yaqin.
- codeGRAPH — lokal LLM va kod bazasi bilan suhbatlashish konsepsiyasiga yaqin.
- Codeknow — dasturiy struktura, bog‘lanishlar va o‘zgarish ta’sirini hisoblashga yaqin.
- Aider yoki OpenHands — kodni real o‘zgartiradigan agent qismini tashkil qilishga mos.
- Semgrep, CodeQL va ast-grep — aniqlik, xavfsizlik hamda strukturaviy tekshiruvni kuchaytiradi.
- Agent Skills va Context7 — tajriba va hujjatlar qatlamini to‘ldiradi.
Bularning mavjudligi sening g‘oyang keraksiz degani emas. Aksincha, qaysi qismlar allaqachon ishlanganini va qaysi chegaralar hali yechilmaganini ko‘rsatadi.
4. Sen qurmoqchi bo‘lgan agent qanday ishlashi kerak?
Men bunday tizimni shunchaki “AI coding assistant” emas, Code Intelligence and Autonomous Engineering Platform deb atagan bo‘lardim.

Uning markazida katta LLM emas, loyiha haqidagi aniq, izlanadigan va yangilanib boradigan bilimlar bazasi turishi kerak.
4.1. Asosiy arxitektura
#chatgpt-mermaid-_r_et_{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:16px;fill:rgb(237, 237, 237);}@keyframes edge-animation-frame{from{stroke-dashoffset:0;}}@keyframes dash{to{stroke-dashoffset:0;}}#chatgpt-mermaid-_r_et_ .edge-animation-slow{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 50s linear infinite;stroke-linecap:round;}#chatgpt-mermaid-_r_et_ .edge-animation-fast{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 20s linear infinite;stroke-linecap:round;}#chatgpt-mermaid-_r_et_ .error-icon{fill:rgb(48, 48, 48);}#chatgpt-mermaid-_r_et_ .error-text{fill:rgb(237, 237, 237);stroke:rgb(237, 237, 237);}#chatgpt-mermaid-_r_et_ .edge-thickness-normal{stroke-width:1px;}#chatgpt-mermaid-_r_et_ .edge-thickness-thick{stroke-width:3.5px;}#chatgpt-mermaid-_r_et_ .edge-pattern-solid{stroke-dasharray:0;}#chatgpt-mermaid-_r_et_ .edge-thickness-invisible{stroke-width:0;fill:none;}#chatgpt-mermaid-_r_et_ .edge-pattern-dashed{stroke-dasharray:3;}#chatgpt-mermaid-_r_et_ .edge-pattern-dotted{stroke-dasharray:2;}#chatgpt-mermaid-_r_et_ .marker{fill:rgb(175, 175, 175);stroke:rgb(175, 175, 175);}#chatgpt-mermaid-_r_et_ .marker.cross{stroke:rgb(175, 175, 175);}#chatgpt-mermaid-_r_et_ svg{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:16px;}#chatgpt-mermaid-_r_et_ p{margin:0;}#chatgpt-mermaid-_r_et_ .label{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";color:rgb(237, 237, 237);}#chatgpt-mermaid-_r_et_ .cluster-label text{fill:rgb(237, 237, 237);}#chatgpt-mermaid-_r_et_ .cluster-label span{color:rgb(237, 237, 237);}#chatgpt-mermaid-_r_et_ .cluster-label span p{background-color:transparent;}#chatgpt-mermaid-_r_et_ .label text,#chatgpt-mermaid-_r_et_ span{fill:rgb(237, 237, 237);color:rgb(237, 237, 237);}#chatgpt-mermaid-_r_et_ .node rect,#chatgpt-mermaid-_r_et_ .node circle,#chatgpt-mermaid-_r_et_ .node ellipse,#chatgpt-mermaid-_r_et_ .node polygon,#chatgpt-mermaid-_r_et_ .node path{fill:rgb(9, 23, 44);stroke:rgb(31, 78, 148);stroke-width:1px;}#chatgpt-mermaid-_r_et_ .rough-node .label text,#chatgpt-mermaid-_r_et_ .node .label text,#chatgpt-mermaid-_r_et_ .image-shape .label,#chatgpt-mermaid-_r_et_ .icon-shape .label{text-anchor:middle;}#chatgpt-mermaid-_r_et_ .node .katex path{fill:#000;stroke:#000;stroke-width:1px;}#chatgpt-mermaid-_r_et_ .rough-node .label,#chatgpt-mermaid-_r_et_ .node .label,#chatgpt-mermaid-_r_et_ .image-shape .label,#chatgpt-mermaid-_r_et_ .icon-shape .label{text-align:center;}#chatgpt-mermaid-_r_et_ .node.clickable{cursor:pointer;}#chatgpt-mermaid-_r_et_ .root .anchor path{fill:rgb(175, 175, 175)!important;stroke-width:0;stroke:rgb(175, 175, 175);}#chatgpt-mermaid-_r_et_ .arrowheadPath{fill:rgb(175, 175, 175);}#chatgpt-mermaid-_r_et_ .edgePath .path{stroke:rgb(175, 175, 175);stroke-width:1px;}#chatgpt-mermaid-_r_et_ .flowchart-link{stroke:rgb(175, 175, 175);fill:none;}#chatgpt-mermaid-_r_et_ .edgeLabel{background-color:rgb(0, 0, 0);text-align:center;}#chatgpt-mermaid-_r_et_ .edgeLabel p{background-color:rgb(0, 0, 0);}#chatgpt-mermaid-_r_et_ .edgeLabel rect{opacity:0.5;background-color:rgb(0, 0, 0);fill:rgb(0, 0, 0);}#chatgpt-mermaid-_r_et_ .labelBkg{background-color:rgba(0, 0, 0, 0.5);}#chatgpt-mermaid-_r_et_ .cluster rect{fill:rgb(48, 48, 48);stroke:rgba(255, 255, 255, 0.15);stroke-width:1px;}#chatgpt-mermaid-_r_et_ .cluster text{fill:rgb(237, 237, 237);}#chatgpt-mermaid-_r_et_ .cluster span{color:rgb(237, 237, 237);}#chatgpt-mermaid-_r_et_ div.mermaidTooltip{position:absolute;text-align:center;max-width:200px;padding:2px;font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:12px;background:rgb(48, 48, 48);border:1px solid rgba(255, 255, 255, 0.15);border-radius:2px;pointer-events:none;z-index:100;}#chatgpt-mermaid-_r_et_ .flowchartTitleText{text-anchor:middle;font-size:18px;fill:rgb(237, 237, 237);}#chatgpt-mermaid-_r_et_ rect.text{fill:none;stroke-width:0;}#chatgpt-mermaid-_r_et_ .icon-shape,#chatgpt-mermaid-_r_et_ .image-shape{background-color:rgb(0, 0, 0);text-align:center;}#chatgpt-mermaid-_r_et_ .icon-shape p,#chatgpt-mermaid-_r_et_ .image-shape p{background-color:rgb(0, 0, 0);padding:2px;}#chatgpt-mermaid-_r_et_ .icon-shape .label rect,#chatgpt-mermaid-_r_et_ .image-shape .label rect{opacity:0.5;background-color:rgb(0, 0, 0);fill:rgb(0, 0, 0);}#chatgpt-mermaid-_r_et_ .label-icon{display:inline-block;height:1em;overflow:visible;vertical-align:-0.125em;}#chatgpt-mermaid-_r_et_ .node .label-icon path{fill:currentColor;stroke:revert;stroke-width:revert;}#chatgpt-mermaid-_r_et_ .node .neo-node{stroke:rgb(31, 78, 148);}#chatgpt-mermaid-_r_et_ [data-look="neo"].node rect,#chatgpt-mermaid-_r_et_ [data-look="neo"].cluster rect,#chatgpt-mermaid-_r_et_ [data-look="neo"].node polygon{stroke:url(#chatgpt-mermaid-_r_et_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-_r_et_ [data-look="neo"].swimlane.cluster rect{filter:none;}#chatgpt-mermaid-_r_et_ [data-look="neo"].node path{stroke:url(#chatgpt-mermaid-_r_et_-gradient);stroke-width:1px;}#chatgpt-mermaid-_r_et_ [data-look="neo"].node .outer-path{filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-_r_et_ [data-look="neo"].node .neo-line path{stroke:rgb(31, 78, 148);filter:none;}#chatgpt-mermaid-_r_et_ [data-look="neo"].node circle{stroke:url(#chatgpt-mermaid-_r_et_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-_r_et_ [data-look="neo"].node circle .state-start{fill:#000000;}#chatgpt-mermaid-_r_et_ [data-look="neo"].icon-shape .icon{fill:url(#chatgpt-mermaid-_r_et_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-_r_et_ [data-look="neo"].icon-shape .icon-neo path{stroke:url(#chatgpt-mermaid-_r_et_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-_r_et_ .node text{font-size:14px;font-weight:600;letter-spacing:normal;fill:rgb(153, 206, 255);}#chatgpt-mermaid-_r_et_ .edgeLabels text{font-size:13px;font-weight:600;letter-spacing:-0.08px;fill:rgb(153, 206, 255);}#chatgpt-mermaid-_r_et_ .node tspan[font-weight="normal"],#chatgpt-mermaid-_r_et_ .edgeLabels tspan[font-weight="normal"]{font-weight:600;}#chatgpt-mermaid-_r_et_ .edgeLabel .label rect{opacity:1;rx:13px;ry:13px;fill:rgb(0, 14, 26);stroke:rgb(26, 62, 95);stroke-width:1px;}#chatgpt-mermaid-_r_et_ .node rect,#chatgpt-mermaid-_r_et_ .node circle,#chatgpt-mermaid-_r_et_ .node ellipse,#chatgpt-mermaid-_r_et_ .node polygon,#chatgpt-mermaid-_r_et_ .node path{fill:rgb(0, 40, 77);stroke:rgba(255, 255, 255, 0.1);stroke-width:1px;}#chatgpt-mermaid-_r_et_ .node rect{rx:16px;ry:16px;}#chatgpt-mermaid-_r_et_ .node.mermaid-decision .label-container{fill:rgb(0, 14, 26);stroke:rgb(26, 62, 95);stroke-dasharray:2,2;}#chatgpt-mermaid-_r_et_ .edgePaths .flowchart-link{stroke:rgb(175, 175, 175);stroke-width:1px;stroke-linecap:round;stroke-linejoin:round;}#chatgpt-mermaid-_r_et_ .marker{fill:rgb(175, 175, 175);stroke:rgb(175, 175, 175);}#chatgpt-mermaid-_r_et_ :root{--mermaid-font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";}Foydalanuvchi topshirig'iOrchestrator AgentVazifani rejalashtirishCode Intelligence EngineAST / Tree-sitterCode Knowledge GraphHybrid Search + RAGDocs va Git tarixiTasdiqlangan kod kontekstiSkill tanlashLocal LLMCheklangan kod o'zgarishlariTests / Lint / Type CheckTekshiruv o'tdimi?Diff va reviewXatoni aniqlash va tuzatishNatija va o'zgarishlarhisobotiHaYo'q





Bu yerda LLM vazifani tushunadi va qaror taklif qiladi. Kodning strukturasi, qidirish, bog‘lanishlarni topish va test bajarish esa ixtisoslashgan vositalar orqali amalga oshadi.

Bu muhim, chunki kichik modeldan barcha bilimlarni yoddan bilishni talab qilmaymiz. Unga kerakli dalillarni tayyorlab beramiz.
4.2. Birinchi qatlam: Codebase Intelligence Engine
Bu tizimning eng muhim qismi bo‘ladi.

Tasavvur qil, yangi repository berildi:
project/
├── frontend/
│   ├── components/
│   ├── pages/
│   ├── services/
│   └── api/
├── backend/
│   ├── routes/
│   ├── controllers/
│   ├── services/
│   ├── models/
│   └── middleware/
├── database/
│   ├── migrations/
│   └── schema.sql
├── tests/
└── docker-compose.yml


Agent har bir faylni LLM'ga yuborib chiqmaydi. Avval kodni dasturiy ravishda tekshiradi va struktura yaratadi.

Bilim grafigida quyidagilar bo‘ladi:
Element	Misol
Frontend komponenti	LoginPage
API endpoint	POST /api/login
Backend funksiyasi	AuthService.login()
Ma’lumotlar modeli	User
Ma’lumotlar bazasi jadvali	users
Middleware	AuthMiddleware
Test	test_login_invalid_password
Konfiguratsiya	JWT_SECRET
Ular orasidagi aloqalar esa quyidagicha ifodalanadi:
LoginPage
    │ CALLS_API
    ▼
POST /api/login
    │ HANDLED_BY
    ▼
AuthController.login()
    │ CALLS
    ▼
AuthService.login()
    │ QUERIES
    ▼
UserRepository
    │ READS
    ▼
users table


Bunday xarita frontend'dan yuborilgan so‘rov backend'da qanday ishlanishini va qayerdan ma’lumot olishini tushuntirishga yordam beradi.

Muhim: bu aloqalarning ba’zilari statik kod tahlili bilan ishonchli aniqlanadi. Boshqalari — masalan, dinamik routing, reflection yoki runtime konfiguratsiya orqali quriladigan yo‘llar — qo‘shimcha tekshiruv talab qiladi. Shuning uchun har bir bog‘lanishga manba fayli, satr raqami va ishonchlilik holati biriktirilishi kerak.
4.3. Ikkinchi qatlam: graph va kontekstli qidiruv
Faqat vector database qo‘yish yetmaydi.

Men uch xil qidiruvni birlashtirgan bo‘lardim:

1. Strukturaviy qidiruv. Funksiya, klass, API endpoint, ma’lumotlar modeli va ularning chaqiruvlarini topadi. Tree-sitter, Codeknow va Aider'ning RepoMap yondashuvlari bu qatlam uchun foydali manbalar. 


GitHub
+1



2. Matnli va semantik qidiruv. Vazifa matniga qarab tegishli kod, izohlar, hujjatlar va tarixiy o‘zgarishlarni topadi.

3. Grafik bo‘ylab qidiruv. Masalan, UserRepository qayerda ishlatilishini yoki muayyan funksiyani o‘zgartirish qaysi endpoint va testlarga ta’sir qilishini aniqlaydi.

Ushbu natijalar birlashtiriladi, keyin kichik modelga faqat vazifaga tegishli kontekst yuboriladi.
4.4. Uchinchi qatlam: Planner va ixtisoslashgan agentlar
Sen “har bir funksiyasini biladigan agent” deding. Men buni hamma narsani bitta LLM'ga topshirish bilan emas, vazifalarni alohida bosqichlarga bo‘lish orqali amalga oshirgan bo‘lardim.

Masalan, foydalanuvchi:
Loyihaga Google orqali login qo‘sh. Frontend, backend va database bilan to‘g‘ri integratsiya qil.

Agent quyidagicha ishlaydi:
1. Repository analyst — mavjud autentifikatsiya arxitekturasini topadi.
2. Planner — qaysi fayllar va qatlamlar o‘zgarishini belgilaydi.
3. Documentation researcher — ishlatilayotgan framework va OAuth kutubxonasining mos hujjatlarini topadi.
4. Implementation agent — kodni mavjud arxitekturaga mos ravishda o‘zgartiradi.
5. Test agent — testlar, type-check va lint tekshiruvlarini ishga tushiradi.
6. Reviewer agent — diff'ni tekshiradi, regressiyalar va ehtimoliy xavfsizlik muammolarini qidiradi.
Bu agentlarning barchasiga alohida katta model kerak emas. Bir xil lokal model turli vazifalar va qat’iy vositalar bilan ishlashi mumkin. Dastlabki bosqichda ko‘p agent yaratishdan ko‘ra, bitta orchestrator ichidagi aniq ish oqimlari va ixtisoslashgan vositalar sodda va ishonchliroq bo‘lishi mumkin.
5. Skill tizimi: agent qanday qilib yaxshi kod yozishni o‘rganadi?
Bu sen ta’kidlagan yana bir juda muhim qism.

Men skill'larni ikki toifaga ajratardim.
A. Engineering skills
Har bir skill'da vazifa qoidalari, kerakli vositalar, misollar va tekshiruvlar bo‘ladi.
skills/
├── understand-repository/
├── add-api-endpoint/
├── add-frontend-feature/
├── database-migration/
├── authentication/
├── debugging/
├── refactoring/
├── performance-analysis/
├── security-review/
└── testing/


Masalan, database-migration skill quyidagilarni talab qiladi:
- mavjud ORM va migratsiya uslubini aniqlash;
- schema va migratsiyalar tarixini o‘qish;
- yangi migratsiya yaratish;
- model va backend kodini moslashtirish;
- migratsiyaning orqaga qaytish holatini tekshirish;
- tegishli testlarni bajarish.
Bu modelga har bir vazifada qaytadan umumiy ko‘rsatmalar yozish zaruratini kamaytiradi.
B. O‘rganuvchi skills
Keyingi bosqichda agent bajarilgan vazifalardan tajriba to‘plashi mumkin.

Masalan:
1. Agent yangi endpoint qo‘shdi.
2. Test xatosi chiqdi.
3. Agent xatoni tuzatdi.
4. Tuzatish va test muvaffaqiyati qayd etildi.
5. Qayta-qayta uchraydigan foydali yechimlar skill yoki qoida sifatida taklif qilindi.
6. Yangi skill keyingi topshiriqlarda alohida test to‘plamida tekshirildi.
CL-Agent kabi loyihalar sessiyalarni qayd etish, qayta ijro qilish va qoidalarni ajratib olish g‘oyalarini o‘rganishga yordam beradi. Lekin har bir muvaffaqiyatli kod bo‘lagini avtomatik ravishda umumiy qoida qilish to‘g‘ri emas: u faqat bitta loyihaga yoki bitta vaziyatga mos bo‘lishi mumkin. 


GitHub



Menimcha, dastlab modellarni fine-tune qilishga shoshilma. Avval skill, kontekst, test va xotira qatlamini yarat. Shunda qaysi muammolarni model xatosi, qaysilarini esa noto‘g‘ri kontekst yoki yetishmayotgan vosita keltirib chiqarganini o‘lchash mumkin bo‘ladi.
6. Internetdan kod topish va mavjud kutubxonalardan foydalanish
Sen Stack Overflow va boshqa manbalardan yaxshi kod topib, loyihaga qo‘shadigan agentni ham xohlaysan.

Bu uchun alohida Research and Documentation Tool kerak.

U quyidagi tartibda ishlashi ma’qul:
1. Avval loyiha ichidan shu funksiyaning mavjud namunalarini qidiradi.
2. Keyin o‘rnatilgan kutubxona versiyasiga mos rasmiy hujjatni topadi.
3. Zarur bo‘lsa, ishonchli GitHub misollari yoki Stack Overflow savollarini qidiradi.
4. Topilgan kodni to‘g‘ridan-to‘g‘ri nusxalamasdan, loyiha arxitekturasi, litsenziyasi va xavfsizlik talablariga mosligini tekshiradi.
5. Kodni testdan o‘tkazadi.
Context7 aynan zamonaviy, versiyaga mos kutubxona hujjatlari va misollarini AI coding agentlariga berish uchun mo‘ljallangan. 


Context7 MCP



E’tibor beradigan jihat: internetdagi kod avtomatik ravishda to‘g‘ri, xavfsiz yoki sening loyihangga mos bo‘lib qolmaydi. Tizim manba havolasini, kod litsenziyasini, foydalanilgan versiyani va test natijasini saqlashi kerak. Internet ishlamasa esa lokal kod bazasi, saqlangan hujjatlar va avval tasdiqlangan yechimlar orqali davom eta olishi lozim.
7. Kichik lokal LLM orqali Opus darajasidagi sifatga qanchalik yaqinlashish mumkin?
Bu yerda men senga aniq farqni aytishim kerak.

8B modelni agent bilan o‘rab qo‘yish uning aql darajasini avtomatik ravishda Opus darajasiga ko‘tarmaydi. Ammo uni ancha foydali dasturiy muhandisga aylantirish mumkin, chunki vazifaning katta qismini modeldan tashqarida ishonchli vositalar bajaradi.
Muammo	Faqat 8B model	Sening agent tiziming
Kerakli faylni topish	Noto‘g‘ri faylni tanlashi mumkin	Indeks va symbol graph orqali qidiradi
Loyihani tushunish	Uzun kontekstni eslab qolishi qiyin	Arxitektura xaritasini saqlaydi
API ishlatish	Eski metod yoki noto‘g‘ri imzo taklif qilishi mumkin	Versiyaga mos hujjatni tekshiradi
Yangi funksiyani qo‘shish	Bog‘liq fayllarni unutishi mumkin	Impact analysis orqali ta’sirlanadigan qismlarni topadi
Koddagi xatoni tuzatish	Faqat taxmin bilan ishlashi mumkin	Testlarni ishga tushirib, xato natijasini qayta ko‘radi
Zaiflikni aniqlash	Muhim holatni ko‘zdan qochirishi mumkin	Statik tahlil va xavfsizlik skanerlaridan foydalanadi
Murakkab vazifani bajarish	Bir urinishda ko‘p xato qilishi mumkin	Rejalashtiradi, kichik o‘zgarishlar qiladi va har bosqichni tekshiradi
Bu yondashuv modelning cheklovlarini yumshatadi, lekin ularni yo‘q qilmaydi. Ayniqsa, yangi algoritm ixtiro qilish, noaniq talablarni to‘g‘ri talqin qilish yoki butunlay noto‘g‘ri arxitektura qaroridan chiqib ketish kabi vazifalarda kuchli modelning afzalligi saqlanadi.

Shuning uchun sening tiziming quyidagi rejimlarda ishlashi mumkin:
- Offline rejim: lokal model, lokal indeks, mahalliy testlar va keshlangan hujjatlar.
- Cloud mavjud bo‘lsa: murakkab rejalashtirish yoki qiyin xatoni tahlil qilish uchun kuchli modelga murojaat qilish.
- Cloud ishlamay qolsa: lokal model topshiriqni kichik bosqichlarda davom ettiradi.
- Mahalliy model ham ishonchsiz bo‘lsa: xavfli o‘zgarishlarni avtomatik qo‘llamasdan, dalillar va bajarilmagan tekshiruvlar hisobotini chiqaradi.
Bu oxirgi holat ham muhim: vazifani davom ettirish degani noto‘g‘ri kodni ko‘r-ko‘rona yozish degani emas.
8. Men sening o‘rningda bo‘lsam, qayerdan boshlardim?
Mavjud loyihalarni bir-biriga ulashni quyidagi tartibda sinab ko‘rardim.

1-bosqich: loyiha haqidagi bilim

Codeknow va GRASP orqali kod xaritasi, dependency tahlili va o‘zgarishlar ta’sirini o‘rgan. Qaysi bog‘lanishlar aniq topilganini va qaysilari faqat taxmin ekanini ajrat.




2-bosqich: lokal coding agent

Aider yoki OpenHands yordamida lokal model bilan kichik, real topshiriqlarni bajartir. Dastlab bitta mavjud loyihangda xato tuzatish, kichik funksiya qo‘shish va test yozishni sinab ko‘r.




3-bosqich: dalillar va tekshiruv

Semgrep, CodeQL va ast-grep orqali kodning xavfsizligi va strukturasini tekshir. Test, lint va type-check natijalarini agentning qaror qabul qilish jarayoniga qo‘sh.




4-bosqich: o‘z agentingni yaratish

O‘z orchestratoring, bilim grafiging, skill tiziming, vazifa xotirasi, model fallback mexanizmi va visualizatsiya interfeysingni qur. Shu bosqichda tayyor loyihalardan qaysi komponentlarni olish, qaysilarini yozish kerakligi tajriba bilan aniq bo‘ladi.



Boshlang‘ich versiyani barcha tillarni birdan qamrab oladigan qilib qurmasdim. Avval Python, JavaScript/TypeScript, SQL va backend API oqimlarini yaxshi tahlil qilishga e’tibor berardim. Chunki frontend → backend → database zanjirini ishonchli ko‘rsatadigan tizim, o‘nlab tillarni yuzaki tahlil qiladigan tizimdan foydaliroq bo‘lishi mumkin.
Yakuniy xulosa
Sening g‘oyangni amalga oshirishning eng to‘g‘ri yo‘li — kod haqidagi bilimni alohida saqlaydigan va kichik LLM’ga uni ishlatishni o‘rgatadigan agent yaratish.

Eng muhim uchta qaror:
1. Modeldan barcha kodni o‘zi tushunishni talab qilma — avval repository'ning tekshiriladigan bilim grafigini yarat.
2. Agentga faqat kod yozish vazifasini bermagin — rejalashtirish, qidirish, tekshirish va xatoni tuzatish uchun alohida vositalar ber.
3. “Kuchli agent”ni katta prompt yoki ko‘p agent bilan o‘lchama — bir xil vazifalar to‘plamida natijaning to‘g‘riligi, test muvaffaqiyati, keraksiz o‘zgarishlar soni va murakkab loyiha bo‘ylab bog‘lanishlarni topish aniqligini o‘lcha.
Eng katta texnik farq aynan shu: oddiy coding chatbot kod yaratadi; sen xohlagan tizim esa kodni topishi, uning nima uchun kerakligini tushuntirishi, o‘zgarishning ta’sirini oldindan baholashi va natijani tekshirgandan keyingina ish tugadi deb hisoblashi kerak.




























1. Modellarning context hajmi qancha?
Oldin gaplashgan uchta modelni taqqoslaylik. Bu yerda model qo‘llab-quvvatlaydigan maksimal kontekst bilan kompyuteringda amalda ishlatiladigan kontekstni farqlash kerak.
Model	Maksimal ko‘rsatilgan context	Model hajmi, Ollama
Qwen2.5-Coder 7B	32K token	4.7 GB  Ollama
Qwen3.5 9B	256K token	6.6–7.6 GB  Ollama
Qwen3-Coder-Next	256K token	52 GB  Ollama
K — ming token. Model hajmi va context limiti Ollama’dagi ko‘rsatilgan variantlarga tegishli; boshqa formatlar yoki kvantlash variantlari farq qilishi mumkin.

256K context juda katta ko‘rinadi. Lekin bu model bir vaqtning o‘zida 256 ming token bilan tez ishlay oladi degani emas.

Sening RTX 3050 8 GB videokartang uchun:
- Qwen2.5-Coder 7B: 8K yoki 16K context bilan boshlashni tavsiya qilaman; 32K'ni keyin sinaysan.
- Qwen3.5 9B: modelning o‘zi VRAM'ning katta qismini band qilishi mumkin. Shuning uchun 256K context borligiga qarab tanlama; 8K–16K bilan ishlashini va xotira sarfini tekshir.
- Qwen3-Coder-Next: mahalliy 8 GB GPU uchun mos emas. Uni 128 GB RAM'li serverda sinash mumkin, ammo 52 GB modelni RAM'da saqlashning o‘zi yetarli emas — KV cache va hisoblash tezligi ham muhim.
Ollama hujjatlarida 24 GiB'dan kam VRAM uchun standart context 4K qilib ko‘rsatilgan. Context'ni oshirish xotira talabini ham oshiradi. Hozirgi haqiqiy qiymatni ollama ps orqali tekshirish mumkin. 


GitHub



2. Ha, agent uchun alohida xotira tizimi yaratish mumkin
Hatto menimcha, sening loyihangda xotira modelning o‘zidan ham muhim arxitektura qismlaridan biri bo‘ladi.

Lekin bitta nozik farqni tushun: context — model hozir ko‘rib turgan ma’lumot; memory — keyingi vazifalarda ham foydalanish uchun saqlangan ma’lumot.

Masalan, agent 100 ming faylli loyihani o‘rgandi. Har safar barcha fayllarni modelga yuborish shart emas. U loyiha xaritasini, oldingi qarorlarini va vazifa tarixini xotirada saqlaydi. Yangi vazifa kelganda kerakli qismlarini qidirib topadi.
3. Men xotirani 5 qatlamli qilardim

1. Working Memory — joriy vazifa xotirasi

Hozirgi topshiriq, bajarilgan qadamlar, qolgan ishlar, xatolar va keyingi harakatlar. Agent qayta ishga tushganda ham vazifa holati saqlanadi.




2. Project Memory — loyiha bilimlari

Frontend, backend, database, API, funksiyalar, bog‘lanishlar, konfiguratsiya va loyiha arxitekturasi. Bu model xotirasidan ko‘ra kod bazasiga bog‘langan, yangilanadigan bilimlar bazasi bo‘ladi.




3. Episodic Memory — tajriba xotirasi

Avval bajarilgan vazifalar, qabul qilingan qarorlar, uchragan xatolar va ularni hal qilgan yechimlar. Keyingi vazifada o‘xshash muammo chiqsa, agent oldingi tajribani topadi.




4. Skill Memory — bajarish usullari

Tasdiqlangan kod yozish tartiblari, debugging usullari, test shablonlari va loyiha qoidalari. Masalan, yangi endpointni qanday qo‘shish va tekshirish.




5. Knowledge Cache — hujjatlar va tashqi bilimlar

Kutubxonalar hujjatlari, versiyaga mos kod misollari va oldin tekshirilgan yechimlar. Internet bo‘lmasa, mavjud keshlangan ma’lumotlardan foydalaniladi.



Bularni beshta alohida AI model qilib yaratish shart emas. Bitta xotira servisi ichida besh xil ma’lumot toifasi sifatida boshlash mumkin.
4. Xotira bilan kontekst qanday hamkorlik qiladi?
Masalan, sen agentga shunday topshiriq berding:
Makondosh loyihasiga foydalanuvchi profilini tahrirlash funksiyasini qo‘sh.

Agent quyidagi jarayonni bajaradi:
1. Xotiradan loyiha haqida ma’lumot oladi

Makondosh Flutter + Django REST Framework ishlatishi, autentifikatsiya mexanizmi, mavjud User modeli va API endpointlarini aniqlaydi.

2. Kod bazasini qayta tekshiradi

Xotiradagi ma’lumotlar joriy kod versiyasiga mosligini tekshiradi, kerakli fayllarni va ularning bog‘lanishlarini topadi.

3. Kerakli bilimlarni context'ga joylaydi

Profil komponenti, tegishli API, model, serializer, permission va testlar. Qolgan minglab fayllar uzatilmaydi.

4. Kod yozadi va tekshiradi

Model o‘zgarishlarni amalga oshiradi, testlar bajariladi va natijalar xotiraga yoziladi. Xato bo‘lsa, tuzatish uchun yangi ma’lumotlar olinadi.

5. Xotira yangilanadi

Yakunlangan vazifa, muhim qarorlar va muvaffaqiyatli tekshiruvlar saqlanadi; eskirgan arxitektura ma’lumotlari esa yangilanadi yoki yaroqsiz deb belgilanadi.


Shunday qilib, model bir necha ming tokenlik kerakli kontekst bilan ishlashi mumkin, xotira esa butun loyiha haqidagi ancha katta hajmdagi bilimlarni saqlab turadi. Albatta, muayyan vazifa uchun kerak bo‘lgan kontekst uning murakkabligiga qarab kattaroq bo‘lishi mumkin.
5. Texnik jihatdan nimada saqlaymiz?
Birinchi versiyada murakkab tizim shart emas. Men quyidagilardan boshlardim:
Komponent	Tavsiya
Vazifa holati va tajriba tarixi	PostgreSQL yoki dastlab SQLite
Kod, funksiya va fayllar grafigi	PostgreSQL jadvallari yoki graph database
Kod va hujjatlarni tez qidirish	Full-text search + embedding qidiruvi
Strukturaviy kod tahlili	Tree-sitter yoki tilga xos AST parserlar
Xotiraning yangilanishini kuzatish	Git commit va fayl hash'lari
Skill'lar	Versiyalanadigan SKILL.md va testlar
Barcha xotira yozuvlari teng ahamiyatga ega bo‘lmaydi. Masalan, “test muvaffaqiyatli o‘tdi” — kuzatilgan fakt. “Bu funksiyani o‘zgartirsak, ehtimol login buziladi” — tekshirilishi kerak bo‘lgan taxmin. Ularni xotirada alohida belgilash lozim.

Yana bir muhim qoida: xotira kodning o‘rnini bosmasin. Agent xotirada AuthService.login() haqidagi eski ma’lumotni topishi mumkin, lekin kod o‘zgargan bo‘lsa, yangi kodni tekshirib olishi shart.
6. Context'ni boshqarishning amaliy rejasi
Sening RTX 3050 8 GB kompyuteringda boshlanishiga Qwen2.5-Coder 7B uchun 8K yoki 16K context bilan sinov qilgan bo‘lardim.

Masalan, 16K tokenlik byudjetni taxminan shunday taqsimlash mumkin:
- 2K — agent qoidalari va topshiriq.
- 6K — joriy vazifaga tegishli kod.
- 3K — loyiha grafigi va oldingi tajriba.
- 2K — API hujjatlari va skill ko‘rsatmalari.
- 3K — model javobi uchun bo‘sh joy va qo‘shimcha kontekst.
Bu qat’iy limit emas, dastlabki loyiha konfiguratsiyasi. Tokenlar taqsimotini haqiqiy vazifalar bo‘yicha o‘zgartirib borish kerak.

Mening yakuniy tavsiyam: avval memory + code graph + hybrid search + bitta coding modelni birlashtir. Keyin har bir tool natijasini umumiy TaskStatega yozib boradigan orchestrator yarat. Shu yondashuv model o‘zgarsa ham saqlanib qoladi va keyinchalik kuchliroq coding modelini ulashni osonlashtiradi.
