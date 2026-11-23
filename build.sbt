name := "traductor-simple"
version := "1.0"
scalaVersion := "3.10.0"

Compile / unmanagedResourceDirectories += baseDirectory.value / "src" / "main" / "prolog"
Compile / run / mainClass := Some("Servidor")