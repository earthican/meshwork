import org.apache.spark.SparkContext
import org.apache.spark.SparkContext._
import org.apache.spark.SparkConf
import org.apache.spark.graphx._
import org.apache.spark.rdd.RDD
import scala.util.control.NonFatal
import java.security.MessageDigest
import java.nio.ByteBuffer
import scala.sys.process._

object edgeList {
    def main(args: Array[String]) {

        // setup the Spark Context
        val conf = new SparkConf().setAppName("CreateEdgeListFile")
        val sc = new SparkContext(conf)

        //val warcFileEdges = "hdfs://ip-172-31-10-101:9000/common-crawl/crawl-data/CC-MAIN-2015-18/segments/1429246633512.41/warc/warc-edges-00000"
        val hdfsPath = "hdfs://"+sys.env("HADOOP_IP")+":9000"
        val warcFileEdges = hdfsPath+"/data/link-edges"

        // md5 hash
        def md5(s: String): Int = {
            val message = MessageDigest.getInstance("MD5").digest(s.getBytes)
            ByteBuffer.wrap(message).getInt
        }

        // function to hash "(src_url, dst_url)" to long integers
        def hashRecord(record: String): String = {
            val error = md5("error").toString
            val r = record.split(" ")
            // Catch ArrayIndexOutOfBoundsException
            try {
                val src_url = r(0)
                val dst_url = r(1)
                md5(src_url).toString + " " + md5(dst_url).toString
            } catch {
                case NonFatal(exc) => error + " " + error
            }
        }

        // read in the data from HDFS
        val rdd = sc.textFile(warcFileEdges)

        // map each record into a tuple consisting of the hash codes of (src_url, dst_url)
        val edgeList = rdd.map(hashRecord).distinct()

        // delete existing directory
        "hdfs dfs -rm -r -f /data/edge-lists" !
        // save the data back into HDFS
        val edgeListFileName = hdfsPath+"/data/edge-lists"
        edgeList.saveAsTextFile(edgeListFileName)

        Console.print("Edge List file saved to /data/edge-lists\n")

    }
}
