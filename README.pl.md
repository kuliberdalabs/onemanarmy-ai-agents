# onemanarmy po polsku

Jednoosobowa firma i armia agentów AI na kilku modelach. To repozytorium jest naszym warsztatem, pokazanym otwarcie: zasady, według których agenci pracują, bramki sprawdzające ich robotę, poziomy uprawnień i evale, z których wynika, który model dostaje które zadanie.

Trzy nawyki trzymają to w całości. Gdy agent pisze „gotowe”, to tylko deklaracja, dopóki ktoś nie sprawdzi prawdziwego pliku, strony albo rekordu. Bramka liczy się dopiero wtedy, gdy raz odrzuciła znany błąd. Model do zadania wybieramy na podstawie pomiarów dla danej klasy zadań.

Dokumentacja jest po angielsku. Wyjątkiem jest kwestionariusz onboardingu, który ma też wersję polską: [onboarding/questionnaire.pl.md](onboarding/questionnaire.pl.md). Ta strona mówi, od czego zacząć.

## Zaczynasz w przyszłym tygodniu

Otwórz [START-HERE.md](START-HERE.md). To ścieżka na około 40 minut, osobno dla Claude Code i dla Codexa:

1. Kopiujesz `core/starter/AGENTS.template.md` do swojego projektu i wypełniasz pola w klamrach.
2. W Claude Code dodajesz hook `doctrine-guard`. Każda zmiana w pliku z zasadami czeka wtedy na Twoją zgodę.
3. Instalujesz skill `session-end`, który na koniec sesji zapisuje stan w pliku projektu. Następny agent zaczyna od folderu, bez szukania w starych czatach.
4. Uruchamiasz `gate-selftest` na przykładowym rejestrze i czytasz wynik. Trzy bramki nie potrafią niczego odrzucić i o to chodzi: tak wygląda sprawdzian, który zawsze mówi „czysto”.

Po każdym kroku jest opisane, co powinno się pojawić na ekranie.

## Już zlecasz pracę agentom

Zacznij od [core/docs/completion-control.md](core/docs/completion-control.md) i [core/docs/controller-worker-contract.md](core/docs/controller-worker-contract.md). Potem puść [core/gate-selftest/](core/gate-selftest/README.md) na własnych bramkach. Jeśli Twoi agenci działają bez pytania o zgodę, przeczytaj [tiers/](tiers/README.md): trzy poziomy uprawnień dla Claude Code i OpenClaw oraz test, który sprawdza, czy poziom faktycznie trzyma.

Pełny opis folderów i ich stanu jest w [README.md](README.md).

Autor: Kuliberda Labs (Kraków), agenci AI i automatyzacje n8n dla firm usługowych. [kuliberda.ai](https://kuliberda.ai)
