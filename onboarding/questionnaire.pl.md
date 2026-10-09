# Wywiad onboardingowy (polski)

Dla: {{OWNER_NAME}}. Osiemnaście pytań, zadawanych po jednym. Gdy odpowiedź jest ogólna ("zależy", "różnie bywa"), dopytaj: świeży, konkretny przykład jest wart więcej niż opis. Jeśli wcześniejsza odpowiedź już pokrywa pytanie, pomiń je i powiedz, że pomijasz. Jeśli właściciel odmawia odpowiedzi, zapisz "odmowa" i idź dalej.

Pod każdym pytaniem jest linia `Zasila:`. Wskazuje, które placeholdery z `context-template/` wypełnia odpowiedź. To notatka dla prowadzącego rozmowę, nie czyta się jej na głos.

Zwracaj się do właściciela w drugiej osobie ("Ty"). Nie odmieniaj placeholdera z imieniem.

## Rola i dzień

### 1. Za jakie decyzje odpowiadasz osobiście?
Dopytaj: o dwie ostatnie prawdziwe decyzje i o to, kto jeszcze brał w nich udział.
Zasila: `{{DECISIONS_OWNED}}`

### 2. Jak wygląda Twój typowy dzień, od pierwszej wiadomości do końca pracy?
Dopytaj: gdzie ucieka czas i co dzieje się o stałych porach.
Zasila: `{{TYPICAL_DAY}}`

### 3. Co przerywa Ci skupienie albo każe wracać do tych samych informacji?
Dopytaj: o ostatni taki przypadek i o to, gdzie w końcu znalazła się odpowiedź.
Zasila: `{{INTERRUPTIONS}}`

## Projekty i ludzie

### 4. Jakie trzy projekty są teraz najważniejsze?
Dopytaj: o jedno zdanie statusu dla każdego. Jak wyglądałoby "idzie dobrze" za miesiąc?
Zasila: `{{PROJECT_1_NAME}}`, `{{PROJECT_1_STATUS}}`, `{{PROJECT_2_NAME}}`, `{{PROJECT_2_STATUS}}`, `{{PROJECT_3_NAME}}`, `{{PROJECT_3_STATUS}}`

### 5. Z kim pracujesz przy każdym z nich i czego oczekujesz od tych osób?
Dopytaj: kto czeka na Ciebie, a na kogo czekasz Ty.
Zasila: `{{PROJECT_1_PEOPLE}}`, `{{PROJECT_2_PEOPLE}}`, `{{PROJECT_3_PEOPLE}}`

### 6. Gdzie dziś zapisujesz decyzje, terminy i ustalenia ze spotkań?
Dopytaj: co ginie po drodze między spotkaniem a tym miejscem.
Zasila: `{{RECORDING_TODAY}}`

## Dokumenty i źródła prawdy

### 7. Na jakich typach dokumentów pracujesz najczęściej?
Dopytaj: które z nich piszesz, a które tylko czytasz.
Zasila: `{{DOCUMENT_TYPES}}`

### 8. Które foldery lub systemy są źródłem prawdy, a które trzymają kopie albo stare wersje?
Dopytaj: gdy dwie wersje się różnią, która wygrywa i kto o tym decyduje.
Zasila: `{{SOURCES_OF_TRUTH}}`, `{{COPIES_AND_STALE}}`

### 9. Jakie dane są wrażliwe i nie mogą trafiać do pamięci asystenta?
Dopytaj: o kategorie (ludzie, pieniądze, zdrowie, dane logowania, materiały klientów) i o konkretne foldery. Nie proś o wklejenie samych danych.
Zasila: `{{NEVER_STORE}}`

## Wyniki

### 10. Jak ma wyglądać dobry poranny brief?
Dopytaj: o długość, kolejność i jedną rzecz, której brief nigdy nie może pominąć.
Zasila: `{{MORNING_BRIEF}}`

### 11. Co wolisz dostać po głosówce: raport, decyzje, zadania, szkic wiadomości czy wszystko naraz?
Dopytaj: w jakiej kolejności i gdzie to ma trafić.
Zasila: `{{VOICE_NOTE_OUTPUT}}`

### 12. Pokaż pięć prawdziwych spraw, na których ocenimy pierwszą wersję.
Dopytaj: wybierz sprawy, które już się wydarzyły, żeby właściciel wiedział, jak wygląda dobra odpowiedź. Dla każdej poproś o oczekiwany wynik w jednym zdaniu.
Zasila: `{{ACCEPTANCE_CASE_1}}`, `{{ACCEPTANCE_CASE_2}}`, `{{ACCEPTANCE_CASE_3}}`, `{{ACCEPTANCE_CASE_4}}`, `{{ACCEPTANCE_CASE_5}}`

## Autonomia

### 13. Co asystent może zapisywać lub zmieniać samodzielnie?
Dopytaj: pliki, foldery, notatki, szkice. Które z tych zmian da się cofnąć i jak.
Zasila: `{{AUTONOMY_ALONE}}`

### 14. Które działania zawsze mają czekać na Twoje potwierdzenie?
Dopytaj: wysyłka czegokolwiek do drugiej osoby, publikacja, usuwanie, wydawanie pieniędzy, wszystko poza folderem roboczym.
Zasila: `{{AUTONOMY_CONFIRM}}`

### 15. Jak szybko i w jakiej formie asystent ma zgłaszać błąd albo konflikt źródeł?
Dopytaj: co jest na tyle pilne, żeby Ci przerwać.
Zasila: `{{ERROR_REPORTING}}`

## Styl

### 16. Pokaż dwie wiadomości lub dokumenty napisane w stylu, który Ci odpowiada.
Dopytaj: co dokładnie Ci się w nich podoba. Jeśli materiały są poufne, poproś o opis stylu zamiast plików.
Zasila: `{{STYLE_SAMPLES}}`

### 17. Jakiego tonu i jakich formatów nie chcesz widzieć?
Dopytaj: o zwroty, emoji, długie wstępy, tabele, wypunktowania i wszystko, co irytuje.
Zasila: `{{STYLE_AVOID}}`

### 18. Jak nazwiesz swojego asystenta?
Dopytaj: nie trzeba. Robocza nazwa wystarczy i można ją potem zmienić.
Zasila: `{{ASSISTANT_NAME}}`
