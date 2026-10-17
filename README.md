# horodater

Ajoute la date locale d'exécution au nom de fichiers, dans leur répertoire
d'origine : `facture.pdf` devient par exemple `20261017_facture.pdf`.
Le contenu et la date de modification du fichier sont conservés. Le changement
de nom peut modifier ses métadonnées, notamment le ctime sous Unix.

## Compatibilité et dépendances

Le programme utilise le shell POSIX (`/bin/sh`), `date` et `mv`. Il ne nécessite
ni Bash spécifiquement, ni Python, ni Git à l'exécution. Les chemins ne passent
pas par `dirname`, `basename`, `realpath` ou des extensions GNU.

Ubuntu est la cible initiale. La CI prévue couvre Ubuntu avec dash et Bash,
ainsi que macOS avec son shell et ses commandes natifs. WSL peut utiliser la
version Linux ; Windows natif n'est pas encore pris en charge.

## Utilisation

```sh
horodater --help
horodater --version
horodater --dry-run -- "facture finale.pdf"
horodater -- "facture finale.pdf" autre.txt
horodater -- -nom-commencant-par-un-tiret.txt
```

Les options doivent précéder les fichiers. `--` termine leur interprétation.
La date `YYYYMMDD` est calculée une seule fois par appel, selon `TZ` ou le
fuseau du système. Elle ne provient pas des métadonnées des fichiers.

- Seuls les fichiers ordinaires sont acceptés. Les répertoires et les liens
  symboliques fournis comme fichiers sont refusés, y compris les liens cassés.
- Un nom commençant par huit chiffres suivis de `_` reste inchangé. Ce critère
  est syntaxique ; il ne valide pas une date du calendrier.
- Toute destination existante est refusée, y compris un répertoire ou un lien
  cassé. Aucun remplacement n'est proposé par une option de force.
- Les opérations sont séquentielles. Une erreur n'empêche pas le traitement
  des arguments suivants ; les opérations déjà réussies restent effectuées.
- `--dry-run` vérifie les fichiers et affiche les opérations prévues sans les
  exécuter. Sa sortie est destinée à la lecture humaine : les noms contenant
  des sauts de ligne peuvent occuper plusieurs lignes. Elle ne réserve aucun nom.
- Fournir deux fois le même fichier peut donner une réussite partielle : le
  second argument désigne alors un fichier devenu absent.

Codes de sortie : **0** si tout réussit ou est déjà préfixé, **1** si une
opération échoue, **2** pour une utilisation invalide. Les erreurs vont sur
stderr ; les renommages effectifs sont silencieux.

### Limite de concurrence

Le contrôle préalable des destinations et `mv -i` avec une entrée fermée
protègent contre les collisions ordinaires et refusent un fichier créé entre
le contrôle et le déplacement. Le programme vérifie aussi le résultat.
Cependant, le `mv` portable n'offre pas de garantie atomique contre un autre
processus qui crée un répertoire ou remplace des chemins pendant l'opération.
Coordonner les écritures concurrentes dans les répertoires concernés ; un lot
n'est pas une transaction. Une garantie plus forte justifierait une autre
implémentation avec des primitives adaptées à chaque système.

## Installation depuis une release

Une release contient une archive `horodater-X.Y.Z.tar.gz` et `SHA256SUMS`.
Vérifier la somme de contrôle avant extraction :

```sh
# Ubuntu / Linux
sha256sum -c SHA256SUMS
# macOS : shasum -a 256 -c SHA256SUMS

tar -xzf horodater-0.1.0.tar.gz
cd horodater-0.1.0
make install PREFIX="$HOME/.local"
"$HOME/.local/bin/horodater" --version
```

Adapter le numéro à la release téléchargée. La somme SHA-256 vérifie
l'intégrité, pas à elle seule l'authenticité de la provenance.

L'installation copie un seul exécutable, sans lien vers les sources. Le dossier
extrait et le dépôt peuvent ensuite être supprimés. Vérifier que
`$HOME/.local/bin` figure dans `PATH` ; aucun fichier de configuration du shell
n'est modifié automatiquement. `make` et `install` servent à l'installation.
Sans `make`, la copie équivalente est :

```sh
install -d "$HOME/.local/bin"
install -m 755 horodater.sh "$HOME/.local/bin/horodater"
```

Pour une installation administrateur : `sudo make install PREFIX=/usr/local`.
Réinstaller une version remplace l'exécutable ; réinstaller une ancienne release
permet de revenir à cette version. Éviter de mélanger plusieurs méthodes
d'installation pour le même chemin.

## Désinstallation

Sans avoir besoin des sources :

```sh
rm -f "$HOME/.local/bin/horodater"
```

Ou depuis le dossier extrait : `make uninstall PREFIX="$HOME/.local"`.
Pour l'installation administrateur : `sudo make uninstall PREFIX=/usr/local`.
Seul l'exécutable est supprimé. Les répertoires partagés et les fichiers
précédemment renommés restent présents.

## Développement et tests

Installer Python 3.9 ou ultérieur et make. Les tests utilisent uniquement la
bibliothèque standard Python (`unittest`) et des fichiers temporaires ; ils
n'ajoutent aucune dépendance au programme installé. Sur Ubuntu :

```sh
sudo apt install make python3 shellcheck
make check
make lint
HORODATER_TEST_SHELL=dash make test
HORODATER_TEST_SHELL=bash make test
```

`make check` valide la syntaxe POSIX et exécute les tests fonctionnels et de
distribution. Les tests couvrent les collisions, les liens, les noms atypiques,
les erreurs, la fin des déplacements avant retour, l'installation hors Git,
la désinstallation et la reproductibilité. Le test des permissions est ignoré
sous root. `make lint` utilise ShellCheck en mode `sh`.
Les doublures de `date` et `mv` supposent que le shell respecte leur résolution
via `PATH` ; cette suite ne vise pas le mode standalone de BusyBox qui peut
utiliser ses applets intégrées à la place.

Conserver les expansions entre guillemets, les messages d'erreur sur stderr
et le contrat CLI stable. Ajouter des tests de comportement pour les corrections.
Le guide `AGENTS.md` initial est conservé ; ce README décrit l'état actuel.

## Fabrication des releases

La version est définie une seule fois dans `HORODATER_VERSION`, au début de
`horodater.sh`. Après mise à jour du journal des changements :

```sh
make check
make lint
SOURCE_DATE_EPOCH=0 make dist
```

Les artefacts sont créés dans `dist/`. Aucun accès réseau ni Git n'est requis
pour les fabriquer, et la recette fonctionne aussi depuis une archive extraite.
La liste des fichiers distribués est explicite dans `tools/dist.py` ; tout
nouveau fichier nécessaire doit y être ajouté. Les métadonnées locales,
secrets et fichiers non listés ne sont pas inclus.

L'ordre, les propriétaires, les permissions et les dates sont normalisés ;
l'en-tête gzip ne contient pas le nom du fichier temporaire. `SOURCE_DATE_EPOCH`
fixe les dates de l'archive (0 par défaut). Les tests comparent deux fabrications
après changement de dossier, des dates et des permissions des sources.
La garantie porte sur les mêmes contenus, la même valeur d'epoch et la même
chaîne Python/zlib. Pour reproduire une release à long terme, conserver les
versions exactes de Python et zlib ou l'image de fabrication utilisée.

Avant publication, partir d'un commit propre, conserver la chaîne de fabrication
et créer un tag `vX.Y.Z` correspondant à la version intégrée. Publier les
artefacts validés et leurs empreintes sans remplacer une release existante.
La CI vérifie les changements mais ne publie rien automatiquement.

Pour préparer ultérieurement un paquet Ubuntu, l'installation accepte le staging :

```sh
make install DESTDIR=/tmp/horodater-package PREFIX=/usr
```

Cela produit `/tmp/horodater-package/usr/bin/horodater`, sans intégrer le chemin
de fabrication au programme. Un paquet `.deb` et une distribution macOS par
gestionnaire de paquets sont des étapes suivantes, pas encore implémentées.

## Licence et évolution

Le projet est sous **GPL-3.0-or-later** : GNU GPL version 3 ou toute version
ultérieure, au choix du destinataire. Le texte figure dans `LICENSE`.

Le shell POSIX reste adapté à cette fonction courte. Une prise en charge de
Windows natif ou des règles plus complexes serait l'occasion d'évaluer Python
(interpréteur requis) ou Go (exécutables par plateforme). Les tests du contrat
CLI pourront accompagner cette migration.
