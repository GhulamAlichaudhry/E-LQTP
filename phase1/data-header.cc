/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
#include "data-header.h"

#include "ns3/log.h"

namespace ns3 {

NS_OBJECT_ENSURE_REGISTERED (DataHeader);

DataHeader::DataHeader ()
  : m_src (0), m_dst (0), m_seq (0), m_hops (0), m_txMs (0)
{
}

TypeId
DataHeader::GetTypeId (void)
{
  static TypeId tid = TypeId ("ns3::DataHeader")
    .SetParent<Header> ()
    .AddConstructor<DataHeader> ()
  ;
  return tid;
}

TypeId
DataHeader::GetInstanceTypeId (void) const
{
  return GetTypeId ();
}

void
DataHeader::Print (std::ostream &os) const
{
  os << "data src=" << m_src << " dst=" << m_dst << " seq=" << m_seq << " hops=" << (int) m_hops;
}

uint32_t
DataHeader::GetSerializedSize (void) const
{
  return 2 + 2 + 2 + 1 + 4;
}

void
DataHeader::Serialize (Buffer::Iterator start) const
{
  start.WriteHtonU16 (m_src);
  start.WriteHtonU16 (m_dst);
  start.WriteHtonU16 (m_seq);
  start.WriteU8 (m_hops);
  start.WriteHtonU32 (m_txMs);
}

uint32_t
DataHeader::Deserialize (Buffer::Iterator start)
{
  m_src = start.ReadNtohU16 ();
  m_dst = start.ReadNtohU16 ();
  m_seq = start.ReadNtohU16 ();
  m_hops = start.ReadU8 ();
  m_txMs = start.ReadNtohU32 ();
  return GetSerializedSize ();
}

} // namespace ns3
