name := "WickedZerg"
version := "1.0.0"
scalaVersion := "3.3.0"

libraryDependencies ++= Seq(
  "org.scala-lang" %% "scala3-compiler" % scalaVersion.value,
  "org.typelevel" %% "cats-core" % "2.10.0"
)

scalacOptions ++= Seq(
  "-deprecation",
  "-feature"
)

mainClass := Some("Main")
