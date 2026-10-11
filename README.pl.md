# onemanarmy po polsku

Jednoosobowa firma i armia agentów AI na kilku modelach. To repozytorium jest naszym warsztatem, pokazanym otwarcie: zasady, według których agenci pracują, bramki sprawdzające ich robotę, poziomy uprawnień i evale, z których wynika, który model dostaje które zadanie.

Trzy nawyki trzymają to w całości. Gdy agent pisze „gotowe”, to tylko deklaracja, dopóki ktoś nie sprawdzi prawdziwego pliku, strony albo rekordu. Bramka liczy się dopiero wtedy, gdy raz odrzuciła znany błąd. Model do zadania wybieramy na podstawie pomiarów dla danej klasy zadań.

Dokumentacja jest po angielsku. Wyjątkiem jest kwestionariusz onboardingu, który ma też wersję polską: [onboarding/questionnaire.pl.md](onboarding/questionnaire.pl.md). Ta strona mówi, od czego zacząć.

Wersja 0.1.0 z 2026-10-13. Potrzebujesz `git`, `bash`, `zsh` i Pythona 3.11 lub nowszego, bez dodatkowych bibliotek. macOS ma git, bash i zsh, ale jego `python3` to 3.9, więc zainstaluj Pythona 3.11 lub nowszego (instalator z python.org albo `brew install python`) i sprawdź, co pokazuje `python3 --version`.

## Od czego zacząć

Otwórz [START-HERE.md](START-HERE.md). To ścieżka na około 40 minut, osobno dla Claude Code i dla Codexa, razem z krokiem 5 i sprawdzeniem w żywej sesji:

1. Kopiujesz `core/starter/AGENTS.template.md` do swojego projektu jako `AGENTS.md` i wypełniasz pola w podwójnych klamrach. W Claude Code kopiujesz też `core/starter/CLAUDE.template.md` jako `CLAUDE.md`: ten plik importuje `AGENTS.md` i trzyma tylko to, co dotyczy samego Claude Code.
2. W Claude Code dodajesz hook `doctrine-guard`. Każda zmiana w `AGENTS.md`, `CLAUDE.md`, plikach `SKILL.md` i ustawieniach narzędzia czeka wtedy na Twoje „tak” albo „nie”. Codex nie ma takiego hooka, więc tę zasadę wpisujesz do `AGENTS.md` jako zwykły tekst.
3. Instalujesz skill `session-end`, który na koniec sesji zapisuje stan w pliku projektu. Następny agent zaczyna od folderu, bez szukania w starych czatach.
4. Uruchamiasz `gate-selftest` na przykładowym rejestrze i czytasz wynik. Trzy bramki nie potrafią niczego odrzucić i o to chodzi: tak wygląda sprawdzian, który zawsze mówi „czysto”.
5. Dajesz agentowi pierwsze prawdziwe zadanie ([examples/first-job](examples/first-job/README.md)): 12 nieuporządkowanych faktur i paragonów do zestawienia wydatków. O tym, czy praca jest skończona, decyduje bramka, którą uruchamiasz sam, a nie słowo agenta.

Między krokiem 4 a 5 jest krótkie sprawdzenie w żywej sesji agenta (około 3 minut), czy agent wczytał zasady, hook i skill. Po każdym kroku jest opisane, co powinno się pojawić na ekranie.

## Już zlecasz pracę agentom

Zacznij od [core/docs/completion-control.md](core/docs/completion-control.md) i [core/docs/controller-worker-contract.md](core/docs/controller-worker-contract.md). Potem puść [core/gate-selftest/](core/gate-selftest/README.md) na własnych bramkach. Jeśli Twoi agenci działają bez pytania o zgodę, przeczytaj [tiers/](tiers/README.md): trzy poziomy uprawnień dla Claude Code i OpenClaw oraz test, który sprawdza, czy poziom faktycznie trzyma.

Pełny opis folderów, ich stanu i wyników testów jest w [README.md](README.md).

## Czym to nie jest

- To nie framework. Nic tutaj nie uruchamia Twoich agentów. Kopiujesz zasady, szablony, nakładki konfiguracji i małe narzędzia na bibliotece standardowej do własnego środowiska.
- To nie zbiór skilli. Rdzeń ma jeden skill. Pakiety wchodzą dopiero wtedy, gdy sami ich używamy i gdy przejdą eval względem gołego modelu. Żaden jeszcze nie wszedł.
- To nie sandbox systemu operacyjnego. Poziomy konfigurują sandboksy i reguły uprawnień, które Twoje narzędzie już ma. Poziom 1 w Claude Code działa na regułach: skrypt, który kasuje pliki w obszarze roboczym, nie wywołuje pytania, bo sandbox pozwala tam zapisywać. Hook `doctrine-guard` łapie narzędzia Edit, Write i MultiEdit, a zapisów z powłoki, takich jak `sed -i`, nie widzi.
- To nie benchmark ani ranking. Każdy eval obejmuje jedną dziedzinę i małe `n`, a wiedza o modelach starzeje się razem z modelami i narzędziami.
- To nie sposób na obejście czyichś warunków. Repozytorium nie zawiera oprogramowania własnościowego, obchodzenia licencji, zbierania danych logowania ani omijania uwierzytelniania. Za przestrzeganie warunków narzędzi i usług, które podłączasz, odpowiadasz Ty.

Autor: Kuliberda Labs (Kraków), agenci AI i automatyzacje n8n dla firm usługowych. [kuliberda.ai](https://kuliberda.ai)
