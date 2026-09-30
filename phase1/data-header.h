/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
#ifndef PHASE1_DATA_HEADER_H
#define PHASE1_DATA_HEADER_H

#include "ns3/header.h"

#include <cstdint>

namespace ns3 {

/** 400-bit-class data packet (LQARP Table II size), unicast toward the USV. */
class DataHeader : public Header
{
public:
  static TypeId GetTypeId (void);
  DataHeader ();
  virtual TypeId GetInstanceTypeId (void) const;
  virtual void Print (std::ostream &os) const;
  virtual uint32_t GetSerializedSize (void) const;
  virtual void Serialize (Buffer::Iterator start) const;
  virtual uint32_t Deserialize (Buffer::Iterator start);

  void SetSrc (uint16_t v) { m_src = v; }
  void SetDst (uint16_t v) { m_dst = v; }
  void SetSeq (uint16_t v) { m_seq = v; }
  void SetHops (uint8_t v) { m_hops = v; }
  void SetTxMs (uint32_t v) { m_txMs = v; }
  uint16_t GetSrc (void) const { return m_src; }
  uint16_t GetDst (void) const { return m_dst; }
  uint16_t GetSeq (void) const { return m_seq; }
  uint8_t GetHops (void) const { return m_hops; }
  uint32_t GetTxMs (void) const { return m_txMs; }

private:
  uint16_t m_src;
  uint16_t m_dst;
  uint16_t m_seq;
  uint8_t m_hops;
  uint32_t m_txMs;
};

} // namespace ns3

#endif
